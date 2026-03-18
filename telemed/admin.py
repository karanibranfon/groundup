from django.contrib import admin
from .models import UserProfile, Patient, Study, Image, ImageProcessingLog, Feedback


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'account_type', 'daily_quota_used', 'quota_reset_date')
    list_filter = ('account_type',)
    search_fields = ('user__username', 'user__email')


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('name', 'patient_id', 'gender', 'email', 'created_at')
    list_filter = ('gender', 'created_at')
    search_fields = ('name', 'patient_id', 'email')


@admin.register(Study)
class StudyAdmin(admin.ModelAdmin):
    list_display = ('patient', 'study_type', 'status', 'created_at', 'report_generated')
    list_filter = ('study_type', 'status', 'created_at')
    search_fields = ('patient__name', 'description')


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'study', 'patient', 'is_dicom', 'created_at')
    list_filter = ('is_dicom', 'created_at')
    search_fields = ('original_filename', 'filename')


@admin.register(ImageProcessingLog)
class ImageProcessingLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action_type', 'image', 'processed_at')
    list_filter = ('action_type', 'processed_at')
    search_fields = ('user__username',)


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'created_at', 'is_resolved')
    list_filter = ('is_resolved', 'created_at')
    search_fields = ('user__username', 'subject', 'message')
