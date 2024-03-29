import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from .utils import fetch_git_sha
from .base import *

GIT_REPO_ROOT = os.path.dirname(BASE_DIR)
PARENT_ROOT = os.path.dirname(GIT_REPO_ROOT)

DEBUG = False

SECRET_KEY = os.environ["SECRET_KEY"]

DEFAULT_FROM_EMAIL = os.environ["DEFAULT_FROM_EMAIL"]
SERVER_EMAIL = os.environ["SERVER_EMAIL"]

SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "true") != 'false'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "true") != 'false'
CSRF_COOKIE_HTTPONLY = True
CSRF_TRUSTED_ORIGINS = os.environ["CSRF_TRUSTED_ORIGINS"].split(',')

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
    integrations=[DjangoIntegration(), RedisIntegration()],
    release=fetch_git_sha(GIT_REPO_ROOT),
    send_default_pii=True,
)

STATICFILES_STORAGE = "core.staticfiles.SourcemapManifestStaticFilesStorage"
STATIC_ROOT = os.path.join(PARENT_ROOT, "public_html", "static")
MEDIA_ROOT = os.path.join(PARENT_ROOT, "public_html", "media")

ACCOUNTS_AVATAR_CHANGE_GROUPS = ["dummy", "Ore_Organization"]
