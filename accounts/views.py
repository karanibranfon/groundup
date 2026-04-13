from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib import messages


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, 'telemed/register.html', {'error': 'Passwords do not match'})
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'telemed/register.html', {'error': 'Username already exists'})
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered')
            return render(request, 'telemed/register.html', {'error': 'Email already registered'})
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        from chat.models import Profile
        Profile.objects.create(user=user, phone=request.POST.get('phone', ''))
        
        login(request, user)
        messages.success(request, f'Welcome, {username}! Your account has been created.')
        return redirect('dashboard')
    
    return render(request, 'telemed/register.html')
