"""
Production settings for PythonAnywhere deployment
"""
from .settings import *

DEBUG = False

ALLOWED_HOSTS = ['kaparo.pythonanywhere.com', 'telemedvision.com', 'localhost', '127.0.0.1']

SECRET_KEY = 'django-insecure-prod-key-change-this'
