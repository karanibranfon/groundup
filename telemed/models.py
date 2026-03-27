from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ('free', 'Free'),
        ('premium', 'Premium'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, default='free')
    daily_quota_used = models.IntegerField(default=0)
    quota_reset_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['quota_reset_date']),
        ]
    
    def __str__(self):
        return f"{self.user.username}'s profile"
    
    def check_and_reset_quota(self):
        today = timezone.now().date()
        if self.quota_reset_date < today:
            self.daily_quota_used = 0
            self.quota_reset_date = today
            self.save(update_fields=['daily_quota_used', 'quota_reset_date'])
    
    @property
    def quota_remaining(self):
        from django.conf import settings
        self.check_and_reset_quota()
        return max(0, settings.DAILY_IMAGE_QUOTA - self.daily_quota_used)
    
    @quota_remaining.setter
    def quota_remaining(self, value):
        pass
    
    @property
    def quota_percent(self):
        from django.conf import settings
        self.check_and_reset_quota()
        if settings.DAILY_IMAGE_QUOTA == 0:
            return 100
        return int((self.daily_quota_used / settings.DAILY_IMAGE_QUOTA) * 100)


class Patient(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    name = models.CharField(max_length=255)
    patient_id = models.CharField(max_length=100, unique=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    email = models.EmailField(blank=True, default='')
    phone = models.CharField(max_length=50, blank=True, default='')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='patients')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['patient_id']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.patient_id})"


class Study(models.Model):
    STUDY_TYPE_CHOICES = [
        ('X-Ray', 'X-Ray'),
        ('CT', 'CT Scan'),
        ('MRI', 'MRI'),
        ('Ultrasound', 'Ultrasound'),
        ('PET', 'PET Scan'),
        ('Other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='studies')
    study_type = models.CharField(max_length=50, choices=STUDY_TYPE_CHOICES)
    description = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='studies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ai_analysis = models.JSONField(null=True, blank=True)
    report_generated = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.study_type} - {self.patient.name}"
    
    @property
    def image_count(self):
        return self.images.count()


class Image(models.Model):
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name='images')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='images', null=True, blank=True)
    filename = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField(default=0)
    content_type = models.CharField(max_length=100, default='application/octet-stream')
    is_dicom = models.BooleanField(default=False)
    dicom_metadata = models.JSONField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='images')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='active')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['study']),
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return self.original_filename
    
    @property
    def patient_obj(self):
        if self.patient:
            return self.patient
        return self.study.patient if self.study else None


class ImageProcessingLog(models.Model):
    ACTION_TYPE_CHOICES = [
        ('view', 'View'),
        ('analyze', 'AI Analysis'),
        ('upload', 'Upload'),
        ('download', 'Download'),
        ('delete', 'Delete'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='processing_logs')
    image = models.ForeignKey(Image, on_delete=models.SET_NULL, null=True, related_name='processing_logs')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPE_CHOICES)
    processed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    details = models.TextField(blank=True, default='')
    
    class Meta:
        ordering = ['-processed_at']
        indexes = [
            models.Index(fields=['user', '-processed_at']),
            models.Index(fields=['image']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.action_type} at {self.processed_at}"


class Feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='feedbacks')
    subject = models.CharField(max_length=255, blank=True, default='')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Feedback from {self.user.username if self.user else 'Anonymous'}"


class EncryptionKey(models.Model):
    ENCRYPTION_MODE_CHOICES = [
        ('itied', 'ITIED (DNA-Chaos, Legacy)'),
        ('itiedc', 'ITIEDC (DNA-Chaos Compression, Legacy)'),
        ('aes_gcm_zstd', 'AES-256-GCM + zstandard (Recommended)'),
    ]
    
    image = models.OneToOneField(
        Image, 
        on_delete=models.CASCADE, 
        related_name='encryption_key',
        help_text="The image this encryption key belongs to"
    )
    mode = models.CharField(
        max_length=15, 
        choices=ENCRYPTION_MODE_CHOICES,
        default='aes_gcm_zstd',
        help_text="Encryption mode used"
    )
    dna_rule = models.IntegerField(
        help_text="DNA encoding rule (1-8) used for this encryption"
    )
    pwlc_p = models.FloatField(
        help_text="PWLCM control parameter p"
    )
    pwlc_x0 = models.FloatField(
        help_text="PWLCM initial value x0"
    )
    sha256_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 hash of the original image"
    )
    encrypted_otp_key = models.BinaryField(
        help_text="OTP key encrypted with master key"
    )
    compression_metadata = models.JSONField(
        null=True, 
        blank=True,
        help_text="Compression metadata for ITIEDC mode (frequency table, etc.)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Encryption Key"
        verbose_name_plural = "Encryption Keys"
        indexes = [
            models.Index(fields=['image']),
            models.Index(fields=['sha256_hash']),
        ]
    
    def __str__(self):
        return f"EncryptionKey for {self.image.filename} (rule={self.dna_rule})"
