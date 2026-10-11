"""Isolated Phase 0 checks: never select a configured production database/provider."""
import os

os.environ.setdefault('DJANGO_SECRET_KEY', 'phase0-local-test-key-not-for-deployment')
os.environ['DATABASE_URL'] = ''
os.environ['DB_ENGINE'] = 'django.db.backends.sqlite3'
from .settings import *  # noqa: E402,F403

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
if os.environ.get('PHASE0_POSTGRES') == '1':
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.postgresql', 'NAME': 'postgres',
        'USER': 'phase0', 'PASSWORD': '', 'HOST': '127.0.0.1', 'PORT': '55432',
        'TEST': {'NAME': 'test_twinpeaks_phase0'},
    }}
DEBUG = False
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1', 'backend.twinpeaksinvestment.com']
SECURE_SSL_REDIRECT = False
STORAGES = {'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
            'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
MOMO_BASE_URL = 'http://127.0.0.1:9'
MOMO_CALLBACK_URL = ''
MOMO_COLLECTION_SUBSCRIPTION_KEY = ''
MOMO_COLLECTION_API_USER = ''
MOMO_COLLECTION_API_KEY = ''
META_PIXEL_ID = ''
META_CONVERSIONS_API_ACCESS_TOKEN = ''
BIRD_API_KEY = ''
