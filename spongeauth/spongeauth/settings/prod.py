import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from .utils import fetch_git_sha
from .base import *

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
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST = "mail.spongepowered.org"
EMAIL_PORT = 587
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
    dsn=os.environ.get("RAVEN_DSN"),
    integrations=[DjangoIntegration()],
    release=fetch_git_sha(GIT_REPO_ROOT),
    send_default_pii=True,
)

STATICFILES_STORAGE = "core.staticfiles.SourcemapManifestStaticFilesStorage"
STATIC_ROOT = os.path.join(PARENT_ROOT, "public_html", "static")
MEDIA_ROOT = os.path.join(PARENT_ROOT, "public_html", "media")

ACCOUNTS_AVATAR_CHANGE_GROUPS = ["dummy", "Ore_Organization"]

if not os.environ.get("DJANGO_SETTINGS_SKIP_LOCAL", False):
    try:
        from .local_settings import *
    except ImportError:
        pass
