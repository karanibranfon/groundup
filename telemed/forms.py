from django import forms
from django.core.validators import FileExtensionValidator
from .models import Patient, Study, Image, Feedback


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['name', 'patient_id', 'date_of_birth', 'gender', 'email', 'phone']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Patient name'}),
            'patient_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Unique patient ID'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1234567890'}),
        }

    def clean_patient_id(self):
        patient_id = self.cleaned_data['patient_id']
        if self.instance.pk:
            if Patient.objects.filter(patient_id=patient_id).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError('Patient ID already exists')
        else:
            if Patient.objects.filter(patient_id=patient_id).exists():
                raise forms.ValidationError('Patient ID already exists')
        return patient_id


class StudyForm(forms.ModelForm):
    class Meta:
        model = Study
        fields = ['patient', 'study_type', 'description', 'status']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'study_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class ImageUploadForm(forms.Form):
    file = forms.FileField(
        validators=[
            FileExtensionValidator(allowed_extensions=['dcm', 'jpg', 'jpeg', 'png', 'tiff', 'tif'])
        ],
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.dcm,.jpg,.jpeg,.png,.tiff,.tif'
        })
    )
    
    def clean_file(self):
        file = self.cleaned_data['file']
        max_size = 50 * 1024 * 1024  # 50MB
        if file.size > max_size:
            raise forms.ValidationError('File size must be less than 50MB')
        return file


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['subject', 'message']
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Your feedback...'}),
        }


class ImageEnhanceForm(forms.Form):
    ENHANCE_CHOICES = [
        ('auto', 'Auto Enhance'),
        ('brightness', 'Brightness'),
        ('contrast', 'Contrast'),
        ('sharpen', 'Sharpen'),
        ('denoise', 'Denoise'),
        ('edge', 'Edge Detection'),
    ]
    
    enhancement_type = forms.ChoiceField(
        choices=ENHANCE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class MeasurementForm(forms.Form):
    MEASUREMENT_TYPES = [
        ('line', 'Line'),
        ('angle', 'Angle'),
        ('area', 'Area'),
        ('ellipse', 'Ellipse'),
        ('arrow', 'Arrow'),
    ]
    
    UNIT_CHOICES = [
        ('mm', 'Millimeters'),
        ('cm', 'Centimeters'),
        ('px', 'Pixels'),
    ]
    
    measurement_type = forms.ChoiceField(choices=MEASUREMENT_TYPES)
    value = forms.FloatField()
    unit = forms.ChoiceField(choices=UNIT_CHOICES)
    x1 = forms.FloatField(widget=forms.HiddenInput())
    y1 = forms.FloatField(widget=forms.HiddenInput())
    x2 = forms.FloatField(widget=forms.HiddenInput())
    y2 = forms.FloatField(widget=forms.HiddenInput())
    label = forms.CharField(max_length=100, required=False)
