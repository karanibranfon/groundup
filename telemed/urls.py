from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('dashboard', views.dashboard, name='app_dashboard'),
    path('send_feedback', views.feedback, name='feedback'),
    path('help', views.help_view, name='help'),
    path('pricing', views.pricing, name='pricing'),
    path('about/testimonials', views.testimonials, name='testimonials'),
    path('video', views.video, name='video'),
    path('terms', views.terms, name='terms'),
    path('privacy', views.privacy, name='privacy'),
    
    path('patients/', views.patients_view, name='patients'),
    path('studies/', views.studies_view, name='studies'),
    path('images/', views.images_view, name='images'),
    path('tools/', views.tools_view, name='tools'),
    path('tools/ai-report', views.ai_report_view, name='ai_report'),
    path('tools/dicom-viewer', views.dicom_viewer_view, name='dicom_viewer'),
    path('tools/enhance', views.enhance_view, name='enhance'),
    path('tools/measure', views.measure_view, name='measure'),
    path('load-sample', views.load_sample, name='load_sample'),
    
    path('api/dashboard/stats', views.dashboard_stats, name='dashboard_stats'),
    path('api/patients', views.patients_list, name='patients_list'),
    path('api/patients/<str:patient_id>', views.patient_detail, name='patient_detail'),
    path('api/studies', views.studies_list, name='studies_list'),
    path('api/studies/<str:study_id>', views.study_detail, name='study_detail'),
    path('api/studies/<str:study_id>/images', views.study_images, name='study_images'),
    path('api/studies/<str:study_id>/generate-report', views.generate_ai_report, name='generate_ai_report'),
    path('api/images/upload', views.upload_image, name='upload_image'),
    path('api/images/<str:image_id>', views.delete_image, name='delete_image'),
    path('api/images/<str:image_id>/file', views.get_image_file, name='get_image_file'),
    path('api/recent/images', views.recent_images, name='recent_images'),
    path('api/recent/studies', views.recent_studies, name='recent_studies'),
    path('api/recent/files', views.recent_files, name='recent_files'),
]
