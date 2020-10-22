import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.rq import RqIntegration

from .utils import fetch_git_sha
from .base import *
import ast

GIT_REPO_ROOT = os.path.dirname(BASE_DIR)
PARENT_ROOT = os.path.dirname(GIT_REPO_ROOT)

DEBUG = False

SECRET_KEY = os.environ["SECRET_KEY"]

DEFAULT_FROM_EMAIL = "admin@spongepowered.org"
SERVER_EMAIL = "admin@spongepowered.org"

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_USE_TLS = os.environ["EMAIL_TLS"] == 'true'
EMAIL_USE_SSL = os.environ["EMAIL_SSL"] == 'true'
EMAIL_HOST = os.environ["EMAIL_HOST"]
EMAIL_PORT = int(os.environ["EMAIL_PORT"])
EMAIL_HOST_USER = os.environ["EMAIL_HOST_USER"]
EMAIL_HOST_PASSWORD = os.environ["EMAIL_HOST_PASSWORD"]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "OPTIONS": {
            "loaders": [
                (
                    "django.template.loaders.cached.Loader",
                    ["django.template.loaders.filesystem.Loader", "django.template.loaders.app_directories.Loader"],
                )
            ],
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

DATABASES["default"]["ATOMIC_REQUESTS"] = True

SSO_ENDPOINTS = {}
for k, v in os.environ.items():
    if not k.startswith("SSO_ENDPOINT_"):
        continue
    k = k[len("SSO_ENDPOINT_") :]
    name, _, key = k.partition("_")
    d = SSO_ENDPOINTS.setdefault(name, {})
    d[key.lower()] = v

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    integrations=[RedisIntegration(),RqIntegration(),DjangoIntegration()],
    release=fetch_git_sha(GIT_REPO_ROOT),
    send_default_pii=True,
    environment=os.environ.get("SENTRY_ENVIRONMENT")
)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["DB_NAME"],
        "USER": os.environ["DB_USER"],
        "PASSWORD": os.environ["DB_PASSWORD"],
        "HOST": os.environ["DB_HOST"],
        "ATOMIC_REQUESTS": True,
    }
}

STATICFILES_STORAGE = "core.staticfiles.SourcemapManifestStaticFilesStorage"
STATIC_ROOT = os.path.join(PARENT_ROOT, "public_html", "static")
MEDIA_ROOT = os.path.join(PARENT_ROOT, "public_html", "media")

ACCOUNTS_AVATAR_CHANGE_GROUPS = ["dummy", "Ore_Organization"]

RQ_QUEUES = {"default": {"HOST": os.environ["REDIS_HOST"], "PORT": 6379, "DB": 0, "DEFAULT_TIMEOUT": 300}}

LETTER_AVATAR_BASE = os.getenv("LETTER_AVATAR_BASE") or "https://forums-cdn.spongepowered.org/" "letter_avatar_proxy/v2/letter/{}/{}/240.png"

if not os.environ.get("DJANGO_SETTINGS_SKIP_LOCAL", False):
    try:
        from .local_settings import *
    except ImportError:
        pass
