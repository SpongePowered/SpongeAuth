import os

from .base import *

if not os.environ.get('DJANGO_SETTINGS_SKIP_LOCAL', False):
    try:
        from .local_settings import *
    except ImportError:
        pass
