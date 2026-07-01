import os
from pathlib import Path
from dotenv import load_dotenv

# =========================
# BASE DIR & ENV
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

# =========================
# CORE SETTINGS
# =========================
SECRET_KEY = os.getenv("SECRET_KEY")
DEBUG = os.getenv("DEBUG", "False") == "True"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")

# =========================
# CLOUDFLARE / PROXY
# =========================
CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "False") == "True"
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False") == "True"

# =========================
# CORE
# =========================
ROOT_URLCONF = 'jett.urls'
WSGI_APPLICATION = 'jett.wsgi.application'

SESSION_COOKIE_AGE = 1209600
SESSION_SAVE_EVERY_REQUEST = True

# Dipakai di crypto field (enkripsi address, phone, date_of_birth)
FIELD_ENCRYPTION_KEY = os.getenv("SECRET_KEY", "")[:32].encode()

# =========================
# TIMEZONE
# =========================
TIME_ZONE = 'Asia/Jakarta'
USE_TZ = True

# =========================
# DATABASE
# =========================
# Build SSL options — hanya aktif kalau DB_SSL_CA ada di .env
_db_ssl = {}
_db_ssl_ca = os.getenv("DB_SSL_CA")
if _db_ssl_ca:
    _db_ssl["ssl"] = {"ca": _db_ssl_ca}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv("DB_NAME"),
        'USER': os.getenv("DB_USER"),
        'PASSWORD': os.getenv("DB_PASSWORD"),
        'HOST': os.getenv("DB_HOST"),
        'PORT': os.getenv("DB_PORT", "3306"),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
            **_db_ssl,
        }
    }
}

# =========================
# AUTH
# =========================
AUTH_USER_MODEL = 'accounts.CustomUser'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8}
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
    {'NAME': 'accounts.validators.StrongPasswordValidator'},
]

# =========================
# AUTHENTICATION BACKENDS
# ← TAMBAHAN: wajib ada untuk django-axes
# =========================
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# =========================
# STATIC & MEDIA
# =========================
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# =========================
# EMAIL (SMTP GMAIL)
# =========================
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")

# =========================
# INSTALLED APPS
# =========================
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Apps JETT
    'accounts.apps.AccountsConfig',
    'jobs',
    'applications',
    'landing',

    # ← TAMBAHAN: rate limiting
    'axes',
]

# =========================
# MIDDLEWARE
# =========================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',

    # ← TAMBAHAN: axes middleware (harus paling bawah)
    'axes.middleware.AxesMiddleware',

    # ← TAMBAHAN: paksa user lengkapi profil sebelum akses halaman lain
    'accounts.middleware.ProfileCompletionMiddleware',
]

# =========================
# DJANGO-AXES (RATE LIMITING)
# =========================
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_LOCKOUT_CALLABLE = None
AXES_RESET_ON_SUCCESS = True
AXES_ENABLE_ADMIN = False
AXES_USERNAME_FORM_FIELD = "email"

# =========================
# TEMPLATES
# =========================
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
            ],
        },
    },
]

# =========================
# LOGGING (SIAP KE SIEM)
# =========================
LOG_DIR = BASE_DIR / "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "jett_fmt": {
            "format": "%(asctime)s JETT ACTION=%(message)s"
        }
    },
    "handlers": {
        "jett_file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": str(LOG_DIR / "application.log"),
            "formatter": "jett_fmt",
        },
    },
    "loggers": {
        "jett": {
            "handlers": ["jett_file"],
            "level": "INFO",
            "propagate": False,
        }
    }
}