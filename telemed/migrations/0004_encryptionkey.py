# Generated migration for EncryptionKey model
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('telemed', '0003_imageprocessinglog_details_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='EncryptionKey',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mode', models.CharField(
                    choices=[('itied', 'ITIED (Encryption Only)'), ('itiedc', 'ITIEDC (Encryption + Compression)')],
                    default='itied',
                    help_text='Encryption mode used',
                    max_length=10
                )),
                ('dna_rule', models.IntegerField(help_text='DNA encoding rule (1-8) used for this encryption')),
                ('pwlc_p', models.FloatField(help_text='PWLCM control parameter p')),
                ('pwlc_x0', models.FloatField(help_text='PWLCM initial value x0')),
                ('sha256_hash', models.CharField(help_text='SHA-256 hash of the original image', max_length=64)),
                ('encrypted_otp_key', models.BinaryField(help_text='OTP key encrypted with master key')),
                ('compression_metadata', models.JSONField(
                    blank=True, 
                    help_text='Compression metadata for ITIEDC mode (frequency table, etc.)', 
                    null=True
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('image', models.OneToOneField(
                    help_text='The image this encryption key belongs to',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='encryption_key',
                    to='telemed.image'
                )),
            ],
            options={
                'verbose_name': 'Encryption Key',
                'verbose_name_plural': 'Encryption Keys',
            },
        ),
        migrations.AddIndex(
            model_name='encryptionkey',
            index=models.Index(fields=['image'], name='telemed_enc_image_id_idx'),
        ),
        migrations.AddIndex(
            model_name='encryptionkey',
            index=models.Index(fields=['sha256_hash'], name='telemed_enc_sha256_idx'),
        ),
    ]
