import os

from .base import *

DEBUG = True
ALLOWED_HOSTS += ['localhost', '127.0.0.1', '::1']
INTERNAL_IPS = ['127.0.0.1', '::1']

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
] + MIDDLEWARE

INSTALLED_APPS = INSTALLED_APPS + [
    'debug_toolbar'
]


if not os.environ.get('DJANGO_SETTINGS_SKIP_LOCAL', False):
    try:
        from .local_settings import *
    except ImportError:
        pass
