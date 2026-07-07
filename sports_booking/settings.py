# sports_booking/settings.py

import os
from pathlib import Path
import dj_database_url

# ✅ Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# ✅ SECRET_KEY
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-key-12345')

# ✅ DEBUG
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# ✅ ALLOWED_HOSTS
ALLOWED_HOSTS = ['*']

# ✅ CSRF_TRUSTED_ORIGINS
CSRF_TRUSTED_ORIGINS = [
    'https://*.railway.app',
    'https://*.up.railway.app',
    'https://*.vercel.app',
]

# ✅ ========== DATABASE ==========
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
    DATABASES['default']['OPTIONS'] = {
        'sslmode': 'require',
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ✅ ========== INSTALLED APPS (تأكد من كل التطبيقات) ==========
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',  # ✅ ده مهم جداً
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
    'crispy_bootstrap5',
    'accounts.apps.AccountsConfig',
    'venues.apps.VenuesConfig',
    'booking.apps.BookingConfig',
    'teams.apps.TeamsConfig',
    'tournaments.apps.TournamentsConfig',
    'dashboard.apps.DashboardConfig',
    'webpush',
    'payment',
    'notifications.apps.NotificationsConfig',
]

# ✅ ========== MIDDLEWARE ==========
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ✅ ========== TEMPLATES ==========
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'notifications.context_processors.unread_count',
            ],
        },
    },
]

# ✅ ========== AUTH ==========
AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'dashboard:home'
LOGOUT_REDIRECT_URL = 'accounts:login'

# ✅ ========== STATIC & MEDIA ==========
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ✅ ========== INTERNATIONALIZATION ==========
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Cairo'
USE_I18N = True
USE_TZ = True

# ✅ ========== OTHER ==========
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880

# ✅ ========== WSGI ==========
WSGI_APPLICATION = 'sports_booking.wsgi.application'
ROOT_URLCONF = 'sports_booking.urls'