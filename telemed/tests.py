from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import date, timedelta
from io import BytesIO
from PIL import Image as PILImage
import os
import numpy as np

from .models import UserProfile, Patient, Study, Image, ImageProcessingLog, Feedback, EncryptionKey
from .services.dna_chaos_encryption import (
    DNACryptoService,
    EncryptionParams,
    PWLCMChaoticMap,
    ArithmeticCoder,
    DNA_BASES,
    DNA_RULES,
    calculate_npcr,
    calculate_uaci,
    calculate_entropy,
)


class UserProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.profile = UserProfile.objects.get(user=self.user)

    def test_profile_creation(self):
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.profile.account_type, 'free')
        self.assertEqual(self.profile.daily_quota_used, 0)

    def test_quota_remaining(self):
        remaining = self.profile.quota_remaining
        self.assertIsInstance(remaining, int)
        self.assertGreaterEqual(remaining, 0)

    def test_quota_reset_on_new_day(self):
        self.profile.daily_quota_used = 5
        self.profile.quota_reset_date = timezone.now().date() - timedelta(days=1)
        self.profile.save()
        
        remaining = self.profile.quota_remaining
        self.assertEqual(remaining, 10)

    def test_str_representation(self):
        self.assertIn('testuser', str(self.profile))


class PatientModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='doctor1', password='testpass123')
        self.patient = Patient.objects.create(
            name='John Doe',
            patient_id='P001',
            date_of_birth=date(1990, 1, 15),
            gender='M',
            email='john@example.com',
            phone='+1234567890',
            created_by=self.user
        )

    def test_patient_creation(self):
        self.assertEqual(self.patient.name, 'John Doe')
        self.assertEqual(self.patient.patient_id, 'P001')
        self.assertEqual(self.patient.gender, 'M')
        self.assertEqual(self.patient.created_by, self.user)

    def test_patient_str(self):
        self.assertIn('John Doe', str(self.patient))
        self.assertIn('P001', str(self.patient))

    def test_unique_patient_id(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Patient.objects.create(
                name='Jane Doe',
                patient_id='P001',
                created_by=self.user
            )


class StudyModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='doctor2', password='testpass123')
        self.patient = Patient.objects.create(
            name='Jane Smith',
            patient_id='P002',
            created_by=self.user
        )
        self.study = Study.objects.create(
            patient=self.patient,
            study_type='X-Ray',
            description='Chest X-Ray',
            created_by=self.user
        )

    def test_study_creation(self):
        self.assertEqual(self.study.study_type, 'X-Ray')
        self.assertEqual(self.study.status, 'draft')
        self.assertEqual(self.study.patient, self.patient)

    def test_study_image_count(self):
        self.assertEqual(self.study.image_count, 0)

    def test_study_ordering(self):
        study2 = Study.objects.create(
            patient=self.patient,
            study_type='CT',
            created_by=self.user
        )
        studies = list(Study.objects.all())
        self.assertEqual(studies[0], study2)


class ImageModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='doctor3', password='testpass123')
        self.patient = Patient.objects.create(
            name='Bob Wilson',
            patient_id='P003',
            created_by=self.user
        )
        self.study = Study.objects.create(
            patient=self.patient,
            study_type='MRI',
            created_by=self.user
        )

    def test_image_creation(self):
        image = Image.objects.create(
            study=self.study,
            patient=self.patient,
            filename='test_mri.jpg',
            original_filename='mri_scan.jpg',
            file_size=1024000,
            created_by=self.user
        )
        self.assertEqual(image.filename, 'test_mri.jpg')
        self.assertEqual(image.original_filename, 'mri_scan.jpg')
        self.assertEqual(image.created_by, self.user)

    def test_image_patient_obj(self):
        image = Image.objects.create(
            study=self.study,
            patient=self.patient,
            filename='test.jpg',
            original_filename='test.jpg',
            created_by=self.user
        )
        self.assertEqual(image.patient_obj, self.patient)


class PatientAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='apiuser', password='testpass123')
        self.client.login(username='apiuser', password='testpass123')
        self.patient = Patient.objects.create(
            name='API Test Patient',
            patient_id='API001',
            created_by=self.user
        )

    def test_list_patients(self):
        response = self.client.get('/api/patients')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('patients', data)
        self.assertEqual(len(data['patients']), 1)

    def test_list_patients_pagination(self):
        for i in range(15):
            Patient.objects.create(
                name=f'Patient {i}',
                patient_id=f'PAG00{i}',
                created_by=self.user
            )
        
        response = self.client.get('/api/patients?limit=5&page=1')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['patients']), 5)
        self.assertEqual(data['pagination']['total'], 16)

    def test_create_patient(self):
        response = self.client.post('/api/patients', {
            'name': 'New Patient',
            'patient_id': 'NEW001',
            'gender': 'F'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Patient.objects.filter(patient_id='NEW001').exists())

    def test_create_patient_duplicate_id(self):
        response = self.client.post('/api/patients', {
            'name': 'Duplicate',
            'patient_id': 'API001'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 409)

    def test_get_patient_detail(self):
        response = self.client.get(f'/api/patients/{self.patient.id}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['name'], 'API Test Patient')

    def test_update_patient(self):
        response = self.client.put(
            f'/api/patients/{self.patient.id}',
            {'name': 'Updated Name'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.name, 'Updated Name')

    def test_delete_patient(self):
        response = self.client.delete(f'/api/patients/{self.patient.id}')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Patient.objects.filter(id=self.patient.id).exists())


class StudyAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='studyuser', password='testpass123')
        self.client.login(username='studyuser', password='testpass123')
        self.patient = Patient.objects.create(
            name='Study Patient',
            patient_id='STUDY001',
            created_by=self.user
        )
        self.study = Study.objects.create(
            patient=self.patient,
            study_type='CT',
            created_by=self.user
        )

    def test_list_studies(self):
        response = self.client.get('/api/studies')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['studies']), 1)

    def test_create_study(self):
        response = self.client.post('/api/studies', {
            'patient_id': self.patient.id,
            'study_type': 'MRI',
            'description': 'Brain MRI'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 201)

    def test_create_study_invalid_type(self):
        response = self.client.post('/api/studies', {
            'patient_id': self.patient.id,
            'study_type': 'InvalidType'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 400)


class DashboardTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='dashuser', password='testpass123')
        self.client.login(username='dashuser', password='testpass123')

    def test_dashboard_requires_login(self):
        self.client.logout()
        response = self.client.get('/dashboard')
        self.assertNotEqual(response.status_code, 200)

    def test_dashboard_accessible(self):
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_stats(self):
        response = self.client.get('/api/dashboard/stats')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('quota_used', data)
        self.assertIn('total_images', data)


class ImageProcessingLogTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='loguser', password='testpass123')
        self.patient = Patient.objects.create(
            name='Log Patient',
            patient_id='LOG001',
            created_by=self.user
        )
        self.study = Study.objects.create(
            patient=self.patient,
            study_type='X-Ray',
            created_by=self.user
        )
        self.image = Image.objects.create(
            study=self.study,
            filename='log_test.jpg',
            original_filename='test.jpg',
            created_by=self.user
        )

    def test_log_creation(self):
        log = ImageProcessingLog.objects.create(
            user=self.user,
            image=self.image,
            action_type='view',
            ip_address='127.0.0.1'
        )
        self.assertEqual(log.action_type, 'view')
        self.assertEqual(log.user, self.user)

    def test_log_ordering(self):
        log1 = ImageProcessingLog.objects.create(
            user=self.user,
            image=self.image,
            action_type='upload'
        )
        log2 = ImageProcessingLog.objects.create(
            user=self.user,
            image=self.image,
            action_type='view'
        )
        logs = list(ImageProcessingLog.objects.all())
        self.assertEqual(logs[0], log2)


class SecurityTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='user1', password='testpass123')
        self.user2 = User.objects.create_user(username='user2', password='testpass123')
        
        self.patient1 = Patient.objects.create(
            name='User1 Patient',
            patient_id='SEC001',
            created_by=self.user1
        )
        self.study1 = Study.objects.create(
            patient=self.patient1,
            study_type='MRI',
            created_by=self.user1
        )
        self.image1 = Image.objects.create(
            study=self.study1,
            filename='user1_image.jpg',
            original_filename='image.jpg',
            created_by=self.user1
        )

    def test_user_cannot_access_other_user_patient(self):
        self.client.login(username='user2', password='testpass123')
        response = self.client.get(f'/api/patients/{self.patient1.id}')
        self.assertEqual(response.status_code, 404)

    def test_user_cannot_access_other_user_study(self):
        self.client.login(username='user2', password='testpass123')
        response = self.client.get(f'/api/studies/{self.study1.id}')
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_access_denied(self):
        response = self.client.get('/api/patients')
        self.assertIn(response.status_code, [401, 403])


class DNACryptoServiceTest(TestCase):
    """Tests for the DNA-Chaos encryption service."""

    def setUp(self):
        self.service = DNACryptoService()
        self.sample_image_data = bytes([i % 256 for i in range(1024)])
        self.width = 32
        self.height = 32

    def test_sha256_to_initial_values(self):
        """Test SHA-256 to initial values derivation."""
        result = self.service.sha256_to_initial_values(self.sample_image_data)
        
        self.assertIn('dna_rule', result)
        self.assertIn('pwlc_p', result)
        self.assertIn('pwlc_x0', result)
        self.assertIn('sha256_hash', result)
        
        self.assertIsInstance(result['dna_rule'], int)
        self.assertIn(result['dna_rule'], range(1, 9))
        self.assertTrue(0 < result['pwlc_p'] < 0.5)
        self.assertTrue(0 < result['pwlc_x0'] < 1)
        self.assertEqual(len(result['sha256_hash']), 64)

    def test_sha256_derivation_deterministic(self):
        """Test that SHA-256 derivation is deterministic."""
        result1 = self.service.sha256_to_initial_values(self.sample_image_data)
        result2 = self.service.sha256_to_initial_values(self.sample_image_data)
        
        self.assertEqual(result1['sha256_hash'], result2['sha256_hash'])
        self.assertEqual(result1['dna_rule'], result2['dna_rule'])

    def test_sha256_different_data_different_hash(self):
        """Test that different data produces different hashes."""
        data1 = b"image_data_1"
        data2 = b"image_data_2"
        
        result1 = self.service.sha256_to_initial_values(data1)
        result2 = self.service.sha256_to_initial_values(data2)
        
        self.assertNotEqual(result1['sha256_hash'], result2['sha256_hash'])


class PWLCMChaoticMapTest(TestCase):
    """Tests for the Piecewise Linear Chaotic Map."""

    def test_pwlc_initialization_valid(self):
        """Test PWLCM initialization with valid parameters."""
        pwlc = PWLCMChaoticMap(x0=0.5, p=0.3)
        self.assertEqual(pwlc.x, 0.5)
        self.assertEqual(pwlc.p, 0.3)

    def test_pwlc_initialization_invalid_x0(self):
        """Test PWLCM rejects invalid x0."""
        with self.assertRaises(ValueError):
            PWLCMChaoticMap(x0=0.0, p=0.3)
        with self.assertRaises(ValueError):
            PWLCMChaoticMap(x0=1.0, p=0.3)

    def test_pwlc_initialization_invalid_p(self):
        """Test PWLCM rejects invalid p."""
        with self.assertRaises(ValueError):
            PWLCMChaoticMap(x0=0.5, p=0.0)
        with self.assertRaises(ValueError):
            PWLCMChaoticMap(x0=0.5, p=0.5)

    def test_pwlc_iterate_returns_correct_length(self):
        """Test PWLCM iteration returns correct number of values."""
        pwlc = PWLCMChaoticMap(x0=0.5, p=0.3)
        result = pwlc.iterate(n=100)
        
        self.assertEqual(len(result), 100)
        self.assertTrue(all(0 <= v <= 1 for v in result))

    def test_pwlc_iterate_updates_state(self):
        """Test that iteration updates internal state."""
        pwlc = PWLCMChaoticMap(x0=0.5, p=0.3)
        initial_x = pwlc.x
        
        pwlc.iterate(n=10)
        
        self.assertNotEqual(pwlc.x, initial_x)

    def test_pwlc_reset(self):
        """Test PWLCM reset functionality."""
        pwlc = PWLCMChaoticMap(x0=0.5, p=0.3)
        pwlc.iterate(n=100)
        
        pwlc.reset(0.7)
        
        self.assertEqual(pwlc.x, 0.7)


class DNACodingTest(TestCase):
    """Tests for DNA encoding and decoding."""

    def setUp(self):
        self.service = DNACryptoService()

    def test_dna_encode_byte_rule_1(self):
        """Test DNA encoding with rule 1."""
        result = self.service.dna_encode_byte(135, rule=1)
        
        self.assertEqual(len(result), 4)
        self.assertTrue(all(base in DNA_BASES for base in result))

    def test_dna_encode_byte_all_rules(self):
        """Test DNA encoding with all 8 rules."""
        for rule in range(1, 9):
            result = self.service.dna_encode_byte(255, rule=rule)
            self.assertEqual(len(result), 4)
            self.assertTrue(all(base in DNA_BASES for base in result))

    def test_dna_decode_byte(self):
        """Test DNA decoding returns original value."""
        original = 135
        encoded = self.service.dna_encode_byte(original, rule=1)
        decoded = self.service.dna_decode_byte(encoded, rule=1)
        
        self.assertEqual(original, decoded)

    def test_dna_roundtrip_all_values(self):
        """Test DNA roundtrip for all possible byte values."""
        for value in range(256):
            for rule in range(1, 9):
                encoded = self.service.dna_encode_byte(value, rule=rule)
                decoded = self.service.dna_decode_byte(encoded, rule=rule)
                self.assertEqual(value, decoded, f"Failed for value {value}, rule {rule}")

    def test_dna_encode_image(self):
        """Test encoding entire image data."""
        image_data = bytes([i % 256 for i in range(100)])
        
        dna_seq = self.service.dna_encode_image(image_data, rule=1)
        
        self.assertEqual(len(dna_seq), len(image_data) * 4)

    def test_dna_decode_image(self):
        """Test decoding entire image data."""
        image_data = bytes([i % 256 for i in range(100)])
        
        dna_seq = self.service.dna_encode_image(image_data, rule=1)
        decoded = self.service.dna_decode_image(dna_seq, rule=1, length=len(image_data))
        
        self.assertEqual(image_data, decoded)


class DNAXORTest(TestCase):
    """Tests for DNA XOR operations."""

    def setUp(self):
        self.service = DNACryptoService()

    def test_dna_xor_operation(self):
        """Test DNA XOR operation."""
        seq1 = "ATGC" * 10
        seq2 = "CGTA" * 10
        
        result = self.service.dna_xor_operation(seq1, seq2, rule=1)
        
        self.assertEqual(len(result), len(seq1))
        self.assertTrue(all(base in DNA_BASES for base in result))

    def test_dna_xor_self_cancels(self):
        """Test that XORing with itself returns original."""
        original = "ATGC" * 10
        
        result = self.service.dna_xor_operation(original, original, rule=1)
        
        self.assertEqual(result, original)

    def test_dna_xor_different_sequences(self):
        """Test XOR produces different result for different sequences."""
        seq1 = "AAAA" * 10
        seq2 = "CCCC" * 10
        
        result = self.service.dna_xor_operation(seq1, seq2, rule=1)
        
        self.assertNotEqual(result, seq1)
        self.assertNotEqual(result, seq2)

    def test_dna_xor_unequal_length_raises(self):
        """Test that XOR with unequal lengths raises error."""
        seq1 = "AAAA"
        seq2 = "AA"
        
        with self.assertRaises(ValueError):
            self.service.dna_xor_operation(seq1, seq2, rule=1)


class OTPGenarationTest(TestCase):
    """Tests for One-Time Pad key generation."""

    def setUp(self):
        self.service = DNACryptoService()
        self.chaotic_seq = np.random.rand(100)

    def test_generate_otp_key_length(self):
        """Test OTP key generation length."""
        length = 50
        
        otp = self.service.generate_otp_key(self.chaotic_seq, length)
        
        self.assertEqual(len(otp), length)

    def test_generate_otp_key_valid_bases(self):
        """Test OTP key contains only valid DNA bases."""
        otp = self.service.generate_otp_key(self.chaotic_seq, length=100)
        
        self.assertTrue(all(base in DNA_BASES for base in otp))


class EncryptionDecryptionTest(TestCase):
    """Tests for full encryption and decryption."""

    def setUp(self):
        self.service = DNACryptoService()
        self.sample_image = bytes([i % 256 for i in range(1024)])
        self.width = 32
        self.height = 32

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encryption followed by decryption returns original."""
        encrypted, params = self.service.encrypt_image(
            self.sample_image, 
            self.width, 
            self.height
        )
        decrypted = self.service.decrypt_image(encrypted, params)
        
        self.assertEqual(self.sample_image, decrypted)

    def test_encrypted_different_from_original(self):
        """Test that encrypted data differs from original."""
        encrypted, params = self.service.encrypt_image(
            self.sample_image,
            self.width,
            self.height
        )
        
        self.assertNotEqual(self.sample_image, encrypted)

    def test_encryption_produces_params(self):
        """Test that encryption returns valid params."""
        encrypted, params = self.service.encrypt_image(
            self.sample_image,
            self.width,
            self.height
        )
        
        self.assertIsInstance(params, EncryptionParams)
        self.assertIn(params.dna_rule, range(1, 9))
        self.assertEqual(params.image_width, self.width)
        self.assertEqual(params.image_height, self.height)

    def test_same_data_same_encryption(self):
        """Test that same data encrypted twice produces same ciphertext (deterministic)."""
        encrypted1, _ = self.service.encrypt_image(self.sample_image, self.width, self.height)
        encrypted2, _ = self.service.encrypt_image(self.sample_image, self.width, self.height)
        
        self.assertEqual(encrypted1, encrypted2)

    def test_different_data_same_params_produces_different(self):
        """Test that different data produces different ciphertext even with same params."""
        data1 = bytes([i for i in range(256)])
        data2 = bytes([255 - i for i in range(256)])
        
        derived = self.service.sha256_to_initial_values(data1)
        params = EncryptionParams(
            dna_rule=derived['dna_rule'],
            pwlc_p=derived['pwlc_p'],
            pwlc_x0=derived['pwlc_x0'],
            sha256_hash=derived['sha256_hash'],
            image_width=32,
            image_height=32
        )
        
        encrypted1, _ = self.service.encrypt_image(data1, 32, 32, params)
        encrypted2, _ = self.service.encrypt_image(data2, 32, 32, params)
        
        self.assertNotEqual(encrypted1, encrypted2)


class CompressionEncryptionTest(TestCase):
    """Tests for encryption with compression (ITIEDC)."""

    def setUp(self):
        self.service = DNACryptoService()
        self.sample_image = bytes([i % 256 for i in range(1024)])
        self.width = 32
        self.height = 32

    def test_encrypt_compress_roundtrip(self):
        """Test encryption+compression followed by decryption+decompression."""
        encrypted, metadata = self.service.encrypt_compress_image(
            self.sample_image,
            self.width,
            self.height
        )
        decrypted = self.service.decrypt_decompress_image(encrypted, metadata)
        
        self.assertEqual(self.sample_image, decrypted)

    def test_compression_metadata_contains_required_fields(self):
        """Test that compression metadata has required fields."""
        _, metadata = self.service.encrypt_compress_image(
            self.sample_image,
            self.width,
            self.height
        )
        
        self.assertIn('params', metadata)
        self.assertIn('frequency', metadata)
        self.assertIn('original_length', metadata)
        self.assertIn('dna_length', metadata)


class MetricsTest(TestCase):
    """Tests for encryption quality metrics."""

    def setUp(self):
        self.sample_original = bytes([i % 256 for i in range(1024)])
        self.sample_encrypted = bytes([(i * 7 + 13) % 256 for i in range(1024)])

    def test_calculate_npcr(self):
        """Test NPCR calculation."""
        npcr = calculate_npcr(self.sample_original, self.sample_encrypted)
        
        self.assertIsInstance(npcr, float)
        self.assertTrue(0 <= npcr <= 100)

    def test_calculate_uaci(self):
        """Test UACI calculation."""
        uaci = calculate_uaci(self.sample_original, self.sample_encrypted)
        
        self.assertIsInstance(uaci, float)
        self.assertTrue(0 <= uaci <= 100)

    def test_calculate_entropy(self):
        """Test entropy calculation."""
        entropy = calculate_entropy(self.sample_original)
        
        self.assertIsInstance(entropy, float)
        self.assertTrue(0 <= entropy <= 8)

    def test_entropy_uniform_data_high(self):
        """Test that uniform data has high entropy."""
        uniform_data = bytes([128] * 1024)
        entropy = calculate_entropy(uniform_data)
        
        self.assertLess(entropy, 1.0)


class EncryptionKeyModelTest(TestCase):
    """Tests for the EncryptionKey model."""

    def setUp(self):
        self.user = User.objects.create_user(username='keyuser', password='testpass123')
        self.patient = Patient.objects.create(
            name='Key Patient',
            patient_id='KEY001',
            created_by=self.user
        )
        self.study = Study.objects.create(
            patient=self.patient,
            study_type='X-Ray',
            created_by=self.user
        )
        self.image = Image.objects.create(
            study=self.study,
            filename='key_test.jpg',
            original_filename='test.jpg',
            created_by=self.user
        )
        self.service = DNACryptoService()

    def test_encryption_key_creation(self):
        """Test creating an encryption key for an image."""
        encrypted, params = self.service.encrypt_image(
            b"test_image_data",
            32,
            32
        )
        
        enc_key = EncryptionKey.objects.create(
            image=self.image,
            mode='itied',
            dna_rule=params.dna_rule,
            pwlc_p=params.pwlc_p,
            pwlc_x0=params.pwlc_x0,
            sha256_hash=params.sha256_hash,
            encrypted_otp_key=encrypted
        )
        
        self.assertEqual(enc_key.image, self.image)
        self.assertEqual(enc_key.dna_rule, params.dna_rule)
        self.assertEqual(enc_key.mode, 'itied')

    def test_encryption_key_itiedc_mode(self):
        """Test creating encryption key with compression mode."""
        encrypted, metadata = self.service.encrypt_compress_image(
            b"test_image_data",
            32,
            32
        )
        
        enc_key = EncryptionKey.objects.create(
            image=self.image,
            mode='itiedc',
            dna_rule=metadata['params'].dna_rule,
            pwlc_p=metadata['params'].pwlc_p,
            pwlc_x0=metadata['params'].pwlc_x0,
            sha256_hash=metadata['params'].sha256_hash,
            encrypted_otp_key=encrypted,
            compression_metadata=metadata
        )
        
        self.assertEqual(enc_key.mode, 'itiedc')
        self.assertIsNotNone(enc_key.compression_metadata)

    def test_encryption_key_unique_per_image(self):
        """Test that each image has exactly one encryption key."""
        EncryptionKey.objects.create(
            image=self.image,
            dna_rule=1,
            pwlc_p=0.3,
            pwlc_x0=0.5,
            sha256_hash='a' * 64,
            encrypted_otp_key=b'key'
        )
        
        with self.assertRaises(Exception):
            EncryptionKey.objects.create(
                image=self.image,
                dna_rule=2,
                pwlc_p=0.4,
                pwlc_x0=0.6,
                sha256_hash='b' * 64,
                encrypted_otp_key=b'key2'
            )

    def test_encryption_key_str_representation(self):
        """Test string representation of encryption key."""
        enc_key = EncryptionKey.objects.create(
            image=self.image,
            dna_rule=3,
            pwlc_p=0.25,
            pwlc_x0=0.7,
            sha256_hash='c' * 64,
            encrypted_otp_key=b'key3'
        )
        
        self.assertIn('key_test.jpg', str(enc_key))
        self.assertIn('rule=3', str(enc_key))


class SecurityPropertiesTest(TestCase):
    """Tests for security properties of the encryption."""

    def setUp(self):
        self.service = DNACryptoService()

    def test_otp_key_encryption_roundtrip(self):
        """Test OTP key can be encrypted and decrypted."""
        otp_key = b"secret_otp_key_data_here_1234567890"
        
        encrypted_otp = self.service.encrypt_otp_key(otp_key)
        decrypted_otp = self.service.decrypt_otp_key(encrypted_otp)
        
        self.assertEqual(otp_key, decrypted_otp)
        self.assertNotEqual(otp_key, encrypted_otp)

    def test_different_master_keys_different_encryption(self):
        """Test that different master keys produce different encrypted OTP."""
        otp_key = b"test_otp_key"
        
        service1 = DNACryptoService(master_key=b"master_key_1")
        service2 = DNACryptoService(master_key=b"master_key_2")
        
        encrypted1 = service1.encrypt_otp_key(otp_key)
        encrypted2 = service2.encrypt_otp_key(otp_key)
        
        self.assertNotEqual(encrypted1, encrypted2)

    def test_params_serialization(self):
        """Test encryption params can be serialized and deserialized."""
        params = EncryptionParams(
            dna_rule=5,
            pwlc_p=0.35,
            pwlc_x0=0.72,
            sha256_hash='e' * 64,
            image_width=512,
            image_height=512
        )
        
        params_dict = self.service.params_to_dict(params)
        restored_params = self.service.dict_to_params(params_dict)
        
        self.assertEqual(params.dna_rule, restored_params.dna_rule)
        self.assertEqual(params.pwlc_p, restored_params.pwlc_p)
        self.assertEqual(params.pwlc_x0, restored_params.pwlc_x0)
        self.assertEqual(params.sha256_hash, restored_params.sha256_hash)
        self.assertEqual(params.image_width, restored_params.image_width)
        self.assertEqual(params.image_height, restored_params.image_height)
