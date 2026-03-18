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
    
    def __str__(self):
        return f"{self.user.username}'s profile"
    
    def check_and_reset_quota(self):
        today = timezone.now().date()
        if self.quota_reset_date < today:
            self.daily_quota_used = 0
            self.quota_reset_date = today
            self.save()
    
    @property
    def quota_remaining(self):
        from django.conf import settings
        self.check_and_reset_quota()
        return max(0, settings.DAILY_IMAGE_QUOTA - self.daily_quota_used)
    
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
    
    class Meta:
        ordering = ['-processed_at']
    
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
