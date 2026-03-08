from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('send_feedback', views.feedback, name='feedback'),
    path('help', views.help_view, name='help'),
    path('pricing', views.pricing, name='pricing'),
    path('login', views.login, name='login'),
    path('signup', views.signup, name='signup'),
    path('about/testimonials', views.testimonials, name='testimonials'),
    path('video', views.video, name='video'),
    path('terms', views.terms, name='terms'),
    path('privacy', views.privacy, name='privacy'),
]
