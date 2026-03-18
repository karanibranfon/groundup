import os
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, FileResponse
from django.conf import settings
from django.utils import timezone
from django.core.paginator import Paginator
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from .models import UserProfile, Patient, Study, Image, ImageProcessingLog, Feedback


def index(request):
    return render(request, 'telemed/index.html')


def feedback(request):
    return render(request, 'telemed/feedback.html')


def help_view(request):
    return render(request, 'telemed/help.html')


def pricing(request):
    return render(request, 'telemed/pricing.html')


def testimonials(request):
    return render(request, 'telemed/testimonials.html')


def video(request):
    return render(request, 'telemed/video.html')


def terms(request):
    return render(request, 'telemed/terms.html')


def privacy(request):
    return render(request, 'telemed/privacy.html')


@login_required
def dashboard(request):
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    user_profile.check_and_reset_quota()
    
    recent_images = Image.objects.filter(created_by=request.user)[:5]
    recent_studies = Study.objects.filter(created_by=request.user)[:5]
    
    context = {
        'username': request.user.username,
        'quota_used': user_profile.daily_quota_used,
        'quota_limit': settings.DAILY_IMAGE_QUOTA,
        'quota_percent': user_profile.quota_percent,
        'quota_remaining': user_profile.quota_remaining,
        'recent_images': recent_images,
        'recent_studies': recent_studies,
        'account_type': user_profile.account_type,
    }
    return render(request, 'telemed/dashboard.html', context)


@login_required
def dashboard_stats(request):
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    user_profile.check_and_reset_quota()
    
    total_images = Image.objects.filter(created_by=request.user).count()
    total_studies = Study.objects.filter(created_by=request.user).count()
    total_patients = Patient.objects.filter(created_by=request.user).count()
    
    return JsonResponse({
        'quota_used': user_profile.daily_quota_used,
        'quota_limit': settings.DAILY_IMAGE_QUOTA,
        'quota_percent': user_profile.quota_percent,
        'quota_remaining': user_profile.quota_remaining,
        'total_images': total_images,
        'total_studies': total_studies,
        'total_patients': total_patients,
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def patients_list(request):
    if request.method == 'GET':
        try:
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 10))
        except (ValueError, TypeError):
            page = 1
            limit = 10
        
        page = max(1, page)
        limit = min(max(1, limit), 100)
        
        search = request.GET.get('search', '').strip()
        
        query = Patient.objects.filter(created_by=request.user)
        if search:
            from django.db.models import Q
            query = query.filter(
                Q(name__icontains=search) | 
                Q(patient_id__icontains=search) |
                Q(email__icontains=search)
            )
        
        paginator = Paginator(query, limit)
        patients = paginator.get_page(page)
        
        data = {
            'patients': [
                {
                    'id': str(p.id),
                    'name': p.name,
                    'patient_id': p.patient_id,
                    'date_of_birth': p.date_of_birth.isoformat() if p.date_of_birth else None,
                    'gender': p.gender,
                    'email': p.email,
                    'phone': p.phone,
                    'created_at': p.created_at.isoformat(),
                }
                for p in patients
            ],
            'pagination': {
                'page': page,
                'limit': limit,
                'total': paginator.count,
                'pages': paginator.num_pages,
            }
        }
        return Response(data)
    
    elif request.method == 'POST':
        data = request.data
        if not data.get('name'):
            return Response({'message': 'Patient name is required'}, status=400)
        if not data.get('patient_id'):
            return Response({'message': 'Patient ID is required'}, status=400)
        
        if Patient.objects.filter(patient_id=data['patient_id']).exists():
            return Response({'message': 'Patient ID already exists'}, status=409)
        
        patient = Patient.objects.create(
            name=data['name'],
            patient_id=data['patient_id'],
            date_of_birth=data.get('date_of_birth'),
            gender=data.get('gender'),
            email=data.get('email', ''),
            phone=data.get('phone', ''),
            created_by=request.user,
        )
        
        ImageProcessingLog.objects.create(
            user=request.user,
            action_type='upload',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details=f'Patient created: {patient.patient_id}'
        )
        
        return Response({
            'id': str(patient.id),
            'name': patient.name,
            'patient_id': patient.patient_id,
        }, status=201)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def patient_detail(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id, created_by=request.user)
    
    if request.method == 'GET':
        return Response({
            'id': str(patient.id),
            'name': patient.name,
            'patient_id': patient.patient_id,
            'date_of_birth': patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            'gender': patient.gender,
            'email': patient.email,
            'phone': patient.phone,
            'created_at': patient.created_at.isoformat(),
            'image_count': patient.images.count(),
        })
    
    elif request.method == 'PUT':
        data = request.data
        if 'name' in data:
            patient.name = data['name']
        if 'email' in data:
            patient.email = data['email']
        if 'phone' in data:
            patient.phone = data['phone']
        if 'date_of_birth' in data:
            patient.date_of_birth = data['date_of_birth']
        if 'gender' in data:
            patient.gender = data['gender']
        patient.save()
        return Response({'message': 'Patient updated successfully'})
    
    elif request.method == 'DELETE':
        if patient.studies.exists():
            return Response({'message': 'Cannot delete patient with existing studies'}, status=400)
        patient.delete()
        return Response({'message': 'Patient deleted successfully'})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def studies_list(request):
    if request.method == 'GET':
        try:
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 10))
        except (ValueError, TypeError):
            page = 1
            limit = 10
        
        page = max(1, page)
        limit = min(max(1, limit), 100)
        
        patient_id = request.GET.get('patientId')
        
        query = Study.objects.filter(created_by=request.user)
        if patient_id:
            query = query.filter(patient_id=patient_id)
        
        paginator = Paginator(query, limit)
        studies = paginator.get_page(page)
        
        data = {
            'studies': [
                {
                    'id': str(s.id),
                    'patient_id': str(s.patient.id),
                    'patient_name': s.patient.name,
                    'study_type': s.study_type,
                    'description': s.description,
                    'status': s.status,
                    'created_at': s.created_at.isoformat(),
                    'image_count': s.image_count,
                }
                for s in studies
            ],
            'pagination': {
                'page': page,
                'limit': limit,
                'total': paginator.count,
                'pages': paginator.num_pages,
            }
        }
        return Response(data)
    
    elif request.method == 'POST':
        data = request.data
        if not data.get('patient_id'):
            return Response({'message': 'Patient ID is required'}, status=400)
        if not data.get('study_type'):
            return Response({'message': 'Study type is required'}, status=400)
        
        valid_types = ['X-Ray', 'CT', 'MRI', 'Ultrasound', 'PET', 'Other']
        if data['study_type'] not in valid_types:
            return Response({'message': f'Invalid study type. Must be one of: {", ".join(valid_types)}'}, status=400)
        
        patient = get_object_or_404(Patient, id=data['patient_id'], created_by=request.user)
        
        study = Study.objects.create(
            patient=patient,
            study_type=data['study_type'],
            description=data.get('description', ''),
            status=data.get('status', 'draft'),
            created_by=request.user,
        )
        
        return Response({
            'id': str(study.id),
            'patient_name': study.patient.name,
            'study_type': study.study_type,
        }, status=201)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def study_detail(request, study_id):
    study = get_object_or_404(Study, id=study_id, created_by=request.user)
    
    if request.method == 'GET':
        return Response({
            'id': str(study.id),
            'patient_id': str(study.patient.id),
            'patient_name': study.patient.name,
            'study_type': study.study_type,
            'description': study.description,
            'status': study.status,
            'created_at': study.created_at.isoformat(),
            'image_count': study.image_count,
            'report_generated': study.report_generated,
            'ai_analysis': study.ai_analysis,
        })
    
    elif request.method == 'PUT':
        data = request.data
        if 'description' in data:
            study.description = data['description']
        if 'status' in data:
            study.status = data['status']
        if 'study_type' in data:
            study.study_type = data['study_type']
        study.save()
        return Response({'message': 'Study updated successfully'})
    
    elif request.method == 'DELETE':
        study.images.all().delete()
        study.delete()
        return Response({'message': 'Study deleted successfully'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_image(request):
    if request.method == 'POST':
        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        user_profile.check_and_reset_quota()
        
        if user_profile.daily_quota_used >= settings.DAILY_IMAGE_QUOTA and user_profile.account_type == 'free':
            return Response({'message': 'Daily image quota exceeded. Please upgrade your account.'}, status=403)
        
        study_id = request.data.get('study_id')
        if not study_id:
            return Response({'message': 'Study ID is required'}, status=400)
        
        study = get_object_or_404(Study, id=study_id, created_by=request.user)
        
        if 'file' not in request.FILES:
            return Response({'message': 'No file provided'}, status=400)
        
        uploaded_file = request.FILES['file']
        
        if uploaded_file.size > settings.MAX_UPLOAD_SIZE:
            return Response({'message': f'File too large. Maximum size is {settings.MAX_UPLOAD_SIZE / (1024*1024)}MB'}, status=400)
        
        filename = uploaded_file.name
        
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
            return Response({'message': f'Invalid file type. Allowed: {", ".join(settings.ALLOWED_IMAGE_EXTENSIONS)}'}, status=400)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        
        upload_dir = settings.UPLOAD_FOLDER
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, unique_filename)
        
        try:
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            return Response({'message': f'Error saving file: {str(e)}'}, status=500)
        
        image = Image.objects.create(
            study=study,
            patient=study.patient,
            filename=unique_filename,
            original_filename=filename,
            file_size=uploaded_file.size,
            content_type=uploaded_file.content_type or 'application/octet-stream',
            is_dicom=ext == 'dcm',
            created_by=request.user,
        )
        
        ImageProcessingLog.objects.create(
            user=request.user,
            image=image,
            action_type='upload',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
        
        user_profile.daily_quota_used += 1
        user_profile.save()
        
        return Response({
            'id': str(image.id),
            'filename': image.filename,
            'original_filename': image.original_filename,
            'file_size': image.file_size,
        }, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def study_images(request, study_id):
    study = get_object_or_404(Study, id=study_id, created_by=request.user)
    images = study.images.all()
    
    return Response({
        'images': [
            {
                'id': str(img.id),
                'filename': img.filename,
                'original_filename': img.original_filename,
                'file_size': img.file_size,
                'is_dicom': img.is_dicom,
                'created_at': img.created_at.isoformat(),
            }
            for img in images
        ]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_image_file(request, image_id):
    image = get_object_or_404(Image, id=image_id, created_by=request.user)
    
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    user_profile.check_and_reset_quota()
    
    ImageProcessingLog.objects.create(
        user=request.user,
        image=image,
        action_type='view',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
    )
    
    file_path = os.path.join(settings.UPLOAD_FOLDER, image.filename)
    if os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'), as_attachment=False, filename=image.original_filename)
    return Response({'message': 'Image file not found'}, status=404)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_image(request, image_id):
    image = get_object_or_404(Image, id=image_id, created_by=request.user)
    
    file_path = os.path.join(settings.UPLOAD_FOLDER, image.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    ImageProcessingLog.objects.create(
        user=request.user,
        action_type='delete',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
    )
    
    image.delete()
    return Response({'message': 'Image deleted successfully'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_images(request):
    try:
        limit = int(request.GET.get('limit', 5))
        limit = min(max(1, limit), 50)
    except (ValueError, TypeError):
        limit = 5
    images = Image.objects.filter(created_by=request.user)[:limit]
    
    return Response({
        'images': [
            {
                'id': str(img.id),
                'study_id': str(img.study.id),
                'study_type': img.study.study_type,
                'filename': img.filename,
                'original_filename': img.original_filename,
                'created_at': img.created_at.isoformat(),
            }
            for img in images
        ]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_studies(request):
    try:
        limit = int(request.GET.get('limit', 5))
        limit = min(max(1, limit), 50)
    except (ValueError, TypeError):
        limit = 5
    studies = Study.objects.filter(created_by=request.user)[:limit]
    
    return Response({
        'studies': [
            {
                'id': str(s.id),
                'patient_id': str(s.patient.id),
                'patient_name': s.patient.name,
                'study_type': s.study_type,
                'status': s.status,
                'created_at': s.created_at.isoformat(),
                'image_count': s.image_count,
            }
            for s in studies
        ]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_files(request):
    try:
        limit = int(request.GET.get('limit', 5))
        limit = min(max(1, limit), 50)
    except (ValueError, TypeError):
        limit = 5
    images = Image.objects.filter(created_by=request.user).order_by('-created_at')[:limit]
    
    return Response({
        'files': [
            {
                'id': str(img.id),
                'filename': img.original_filename,
                'path': f"media/uploads/{img.filename}",
                'file_size': img.file_size,
                'created_at': img.created_at.isoformat(),
            }
            for img in images
        ]
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_ai_report(request, study_id):
    study = get_object_or_404(Study, id=study_id, created_by=request.user)
    
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    user_profile.check_and_reset_quota()
    
    if user_profile.daily_quota_used >= settings.DAILY_IMAGE_QUOTA and user_profile.account_type == 'free':
        return Response({'message': 'Daily image quota exceeded. Please upgrade your account.'}, status=403)
    
    images = study.images.all()
    if not images.exists():
        return Response({'message': 'No images found for this study'}, status=400)
    
    mock_analysis = {
        'summary': f'AI analysis for {study.study_type} study with {images.count()} images',
        'confidence': 0.92,
        'findings': [
            'No acute abnormalities detected',
            'Normal anatomical structures visualized',
            'Comparison with prior studies recommended if available',
        ],
        'recommendations': [
            'Clinical correlation recommended',
            'Follow-up imaging in 6-12 months if clinically indicated',
        ],
    }
    
    study.ai_analysis = mock_analysis
    study.report_generated = True
    study.save()
    
    user_profile.daily_quota_used += 1
    user_profile.save()
    
    ImageProcessingLog.objects.create(
        user=request.user,
        image=images.first(),
        action_type='analyze',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
    )
    
    return Response({
        'message': 'AI report generated successfully',
        'analysis': mock_analysis,
    })


@login_required
def patients_view(request):
    patients_list = Patient.objects.filter(created_by=request.user).order_by('-created_at')
    paginator = Paginator(patients_list, 20)
    page = request.GET.get('page', 1)
    patients = paginator.get_page(page)
    return render(request, 'telemed/patients.html', {'patients': patients})


@login_required
def studies_view(request):
    study_filter = request.GET.get('type', 'all')
    
    studies_list = Study.objects.filter(created_by=request.user).select_related('patient')
    if study_filter != 'all':
        studies_list = studies_list.filter(study_type=study_filter)
    
    paginator = Paginator(studies_list, 20)
    page = request.GET.get('page', 1)
    studies = paginator.get_page(page)
    
    patients = Patient.objects.filter(created_by=request.user)
    
    return render(request, 'telemed/studies.html', {
        'studies': studies,
        'patients': patients,
        'study_filter': study_filter,
    })


@login_required
def images_view(request):
    study_id = request.GET.get('study')
    
    images_list = Image.objects.filter(created_by=request.user).select_related('study', 'patient')
    if study_id:
        images_list = images_list.filter(study_id=study_id)
    
    paginator = Paginator(images_list, 24)
    page = request.GET.get('page', 1)
    images = paginator.get_page(page)
    
    studies = Study.objects.filter(created_by=request.user).select_related('patient')
    
    return render(request, 'telemed/images.html', {
        'images': images,
        'studies': studies,
        'selected_study': study_id,
    })


@login_required
def tools_view(request):
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    user_profile.check_and_reset_quota()
    
    recent_logs = ImageProcessingLog.objects.filter(
        user=request.user,
        action_type__in=['view', 'analyze']
    ).select_related('image', 'image__study', 'image__patient')[:10]
    
    return render(request, 'telemed/tools.html', {
        'recent_logs': recent_logs,
        'quota_used': user_profile.daily_quota_used,
        'quota_limit': settings.DAILY_IMAGE_QUOTA,
        'quota_percent': user_profile.quota_percent,
        'quota_remaining': user_profile.quota_remaining,
    })


@login_required
def ai_report_view(request):
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    user_profile.check_and_reset_quota()
    
    studies = Study.objects.filter(created_by=request.user).select_related('patient')
    
    return render(request, 'telemed/ai_report.html', {
        'studies': studies,
        'quota_used': user_profile.daily_quota_used,
        'quota_limit': settings.DAILY_IMAGE_QUOTA,
        'quota_percent': user_profile.quota_percent,
        'quota_remaining': user_profile.quota_remaining,
    })


@login_required
def dicom_viewer_view(request):
    studies = Study.objects.filter(created_by=request.user).select_related('patient')
    return render(request, 'telemed/viewer.html', {'studies': studies})


@login_required
def load_sample(request):
    sample_type = request.GET.get('type')
    
    sample_mapping = {
        'knee_mri': ('knee_mri.jpg', 'Knee MRI Sample', 'MRI'),
        'chest_xray': ('chest_xray.jpg', 'Chest X-Ray Sample', 'X-Ray'),
        'ct_scan': ('ct_scan.jpg', 'CT Scan Sample', 'CT'),
    }
    
    if sample_type not in sample_mapping:
        return redirect('dashboard')
    
    filename, title, study_type = sample_mapping[sample_type]
    sample_path = os.path.join(settings.BASE_DIR, 'static', 'samples', filename)
    
    if not os.path.exists(sample_path):
        return redirect('dashboard')
    
    return FileResponse(
        open(sample_path, 'rb'),
        as_attachment=False,
        filename=filename
    )


@login_required
def enhance_view(request):
    studies = Study.objects.filter(created_by=request.user).select_related('patient')
    return render(request, 'telemed/enhance.html', {'studies': studies})


@login_required
def measure_view(request):
    studies = Study.objects.filter(created_by=request.user).select_related('patient')
    return render(request, 'telemed/measure.html', {'studies': studies})
