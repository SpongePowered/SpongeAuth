import os

from .base import *

IS_TESTING = True

if not os.environ.get("DJANGO_SETTINGS_SKIP_LOCAL", False):
    try:
        from .local_settings import *
    except ImportError:
        pass
