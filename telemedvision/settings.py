"""
Django settings for telemedvision.
co authored by open code
"""

import os
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()

try:
    environ.Env.read_env(os.path.join(BASE_DIR, '.env'))
except FileNotFoundError:
    pass

SECRET_KEY = env('SECRET_KEY', default='django-insecure-change-me-in-production')

DEBUG = env.bool('DEBUG', default=False)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1', 'kaparo.pythonanywhere.com', 'telemedvision.com'])

APPEND_SLASH = True




INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'accounts',
    'telemed',
    'chat',
    'channels',
    'blog',
    'syringly',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'telemedvision.middleware.RateLimitMiddleware',
    'telemedvision.middleware.HealthCheckMiddleware',
]

ROOT_URLCONF = 'telemedvision.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'telemedvision' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'telemedvision.wsgi.application'


# Database
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Africa/Nairobi'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# Image upload folders (in static for serving)
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ENCRYPTED_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'encrypted')
DECRYPTED_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'decrypted')

# Image processing quota (free tier)
DAILY_IMAGE_QUOTA = 10
QUOTA_RESET_HOUR = 0

# Allowed file types
ALLOWED_IMAGE_EXTENSIONS = {'dcm', 'jpg', 'jpeg', 'png', 'tiff', 'tif'}
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# JWT Settings
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Login URL
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'app_dashboard'
LOGOUT_REDIRECT_URL = 'login'

# Email settings (configure for production)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = 'localhost'
EMAIL_PORT = 25
EMAIL_USE_TLS = False
DEFAULT_FROM_EMAIL = 'noreply@telemedvision.com'

# Channels
ASGI_APPLICATION = 'telemedvision.asgi.application'
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [env('REDIS_URL', default='redis://localhost:6379')],
        },
    }
}

# LLM Configuration for AI Blog Writing
LLM_PROVIDER = env('LLM_PROVIDER', default='openai')
OPENAI_MODEL = env('OPENAI_MODEL', default='gpt-4o')
OPENAI_API_KEY = env('OPENAI_API_KEY', default='')
ANTHROPIC_MODEL = env('ANTHROPIC_MODEL', default='claude-sonnet-4-20250514')
ANTHROPIC_API_KEY = env('ANTHROPIC_API_KEY', default='')
OLLAMA_BASE_URL = env('OLLAMA_BASE_URL', default='http://localhost:11434')
OLLAMA_MODEL = env('OLLAMA_MODEL', default='llama3')

# Rate limiting settings
RATE_LIMIT_ENABLED = env.bool('RATE_LIMIT_ENABLED', default=True)
RATE_LIMIT_PER_MINUTE = env.int('RATE_LIMIT_PER_MINUTE', default=60)
RATE_LIMIT_PER_HOUR = env.int('RATE_LIMIT_PER_HOUR', default=1000)
