"""Django settings for the blog-style project."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from envs/.env if present
load_dotenv(BASE_DIR / "envs" / ".env")

# Basic configuration -----------------------------------------------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [host for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost 127.0.0.1 [::1]").split() if host]

CSRF_TRUSTED_ORIGINS = [origin for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split() if origin]

# Applications -------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "django_extensions",
    "ckeditor",
    "ckeditor_uploader",
    "app.post",
    "app.bike",
    "app.submission",
    "app.user",
    "app.studio",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database -----------------------------------------------------------------
if os.getenv("USE_SQLITE", "0") == "1":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "spokit"),
            "USER": os.getenv("POSTGRES_USER", "spokit"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "spokit"),
            "HOST": os.getenv("POSTGRES_HOST", "db"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }

# Password validation ------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization -----------------------------------------------------
LANGUAGE_CODE = os.getenv("DJANGO_LANGUAGE_CODE", "ko-kr")
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "Asia/Seoul")
USE_I18N = True
USE_TZ = True

# Static & media -----------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_IMAGE_BACKEND = "pillow"
CKEDITOR_ALLOW_NONIMAGE_FILES = False
CKEDITOR_CONFIGS = {
    "default": {
        "toolbar": [
            {"name": "clipboard", "items": ["Undo", "Redo"]},
            {"name": "basicstyles", "items": ["Bold", "Italic", "Underline", "RemoveFormat"]},
            {"name": "paragraph", "items": [
                "NumberedList", "BulletedList", "-", "Outdent", "Indent", "-",
                "JustifyLeft", "JustifyCenter", "JustifyRight", "JustifyBlock"
            ]},
            {"name": "insert", "items": ["Image", "Table", "HorizontalRule", "SpecialChar"]},
            {"name": "links", "items": ["Link", "Unlink"]},
            {"name": "styles", "items": ["Format", "Font", "FontSize"]},
            {"name": "colors", "items": ["TextColor", "BGColor"]},
            {"name": "tools", "items": ["Maximize", "Source"]},
        ],
        "height": 400,
        "width": "100%",
        "extraPlugins": (
            "uploadimage,image2,widget,lineutils,clipboard," \
            "pastefromword,font,justify,colorbutton,colordialog"
        ),

        "removePlugins": "image",           # 기본 이미지 플러그인 제거(이미지2 사용)
        "filebrowserUploadUrl": "/ckeditor/upload/",
        "filebrowserBrowseUrl": "/ckeditor/browse/",
        "imageUploadUrl": "/ckeditor/upload/",
        "allowedContent": True,             # 사용자가 직접 스타일 조절 가능
        "image2_alignClasses": ["img-left", "img-center", "img-right"],
        "image2_disableResizer": False,     # 우측 하단에서 드래그로 크기 조절
        "autoGrow_onStartup": True,
        "autoGrow_minHeight": 300,
        "removeDialogTabs": "link:advanced;image:advanced",
    }
}


# Default primary key ------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework --------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Spokit API",
    "DESCRIPTION": "Spokit 서비스 기능을 위한 OpenAPI 문서",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# Authentication ----------------------------------------------------------
LOGIN_URL = "user:login"
LOGIN_REDIRECT_URL = "user:profile"
LOGOUT_REDIRECT_URL = "post:list"

# Logging ------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
    },
}


# Submission form configuration -------------------------------------------
SUBMISSION_STORY_TEMPLATE_URL = os.getenv("SUBMISSION_STORY_TEMPLATE_URL", "")
