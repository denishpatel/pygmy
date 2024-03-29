"""
Django settings for pygmy project.

Generated by 'django-admin startproject' using Django 3.0.6.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

env_path = Path(BASE_DIR) / '.env'
load_dotenv(dotenv_path=env_path)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '&9$6tb)8x_pnj1x68t9#t1wwb&@ns0=n8#j94_@_-!rx_ar1^@'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'drf_yasg2',
    'corsheaders',
    'django_filters',

    # user installed apps
    'pygmy',
    'engine',
    'users',
    'webapp',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ORIGIN_ALLOW_ALL = True

ROOT_URLCONF = 'pygmy.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'pygmy.wsgi.application'

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

if sys.platform == "win32":
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'pygmy',
            'USER': 'postgres',
            'PASSWORD': 'root12345',
            'HOST': 'localhost',
            'PORT': 5432,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': os.environ.get("DB_NAME"),
            'USER': os.environ.get("DB_USER"),
            'PASSWORD': os.environ.get("DB_PASSWORD"),
            'HOST': os.environ.get("DB_HOST"),
            'PORT': 5432,
        }
    }

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# setting user model to custom user model
AUTH_USER_MODEL = 'users.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'users.authentication.BearerAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework_datatables.filters.DatatablesFilterBackend',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
        'rest_framework_datatables.renderers.DatatablesRenderer',
    )
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_URL = '/static/'

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
    'LOGIN_URL': '/api/login',
}

REDOC_SETTINGS = {
    'LAZY_RENDERING': False,
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

DEFAULT_REGION = "us-east-1"

# Login Redirect to
LOGIN_REDIRECT_URL = 'landing'
LOGIN_URL = "login"

STATIC_ROOT = os.path.join(BASE_DIR, "static")

# Filter Tag values
EC2_INSTANCE_POSTGRES_TAG_KEY_NAME = "Role"
EC2_INSTANCE_POSTGRES_TAG_KEY_VALUE = "PostgreSQL"

# Read Tag Values
EC2_INSTANCE_PROJECT_TAG_KEY_NAME = "Project"
EC2_INSTANCE_ENV_TAG_KEY_NAME = "Environment"
EC2_INSTANCE_CLUSTER_TAG_KEY_NAME = "Cluster"

# When inspecting role-based cluster topology, use this tag name to determine the role a DB node has
EC2_INSTANCE_ROLE_TAG_KEY_NAME = "PGRole"

# If you wish to restrict the instances Pygmy will find to a subset of VPCs available, enumerate them with EC2_INSTANCE_VPC_MENU
# Leaving the array empty will let Pygmy search all VPCs it would normally find.
EC2_INSTANCE_VPC_MENU = []

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'simple': {
            'format': '%(asctime)s [%(process)d] %(levelname)s - %(name)s : %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'pygmyLogs': {
            'class': 'logging.handlers.RotatingFileHandler',
            'maxBytes': 1024*1024*50,  # 50 MB
            'backupCount': 5,
            'formatter': 'simple',
            'filename': os.path.join(BASE_DIR, 'logs', 'error.log'),
        },
        'db_log': {
            'class': 'pygmy.db_logger.DBHandler'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'pygmyLogs'],
            'level': 'INFO',
            'propagate': True,
        },
        'engine': {
            'handlers': ['console', 'pygmyLogs', 'db_log'],
            'level': 'INFO',
            'propagate': True,
        },
        'webapp': {
            'handlers': ['console', 'pygmyLogs', 'db_log'],
            'level': 'INFO',
            'propagate': True,
        },
        'users': {
            'handlers': ['console', 'pygmyLogs', 'db_log'],
            'level': 'INFO',
            'propagate': True,
        },
    }
}
