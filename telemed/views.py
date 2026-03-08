from django.shortcuts import render


def index(request):
    return render(request, 'telemed/index.html')


def feedback(request):
    return render(request, 'telemed/feedback.html')


def help_view(request):
    return render(request, 'telemed/help.html')


def pricing(request):
    return render(request, 'telemed/pricing.html')


def login(request):
    return render(request, 'telemed/login.html')


def signup(request):
    return render(request, 'telemed/register.html')


def testimonials(request):
    return render(request, 'telemed/testimonials.html')


def video(request):
    return render(request, 'telemed/video.html')


def terms(request):
    return render(request, 'telemed/terms.html')


def privacy(request):
    return render(request, 'telemed/privacy.html')
