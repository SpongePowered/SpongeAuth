import os

from .base import *

DEBUG = True
ALLOWED_HOSTS += ["localhost", "127.0.0.1", "::1"]
CSRF_TRUSTED_ORIGINS = ["http://localhost"]
INTERNAL_IPS = ["127.0.0.1", "::1"]
REQUIRE_EMAIL_CONFIRM = False

MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE

INSTALLED_APPS = INSTALLED_APPS + ["debug_toolbar"]

for queue in RQ_QUEUES.values():
    queue["ASYNC"] = False
from fakeredis import FakeRedis, FakeStrictRedis
import django_rq.queues

django_rq.queues.get_redis_connection = lambda _, strict: FakeStrictRedis() if strict else FakeRedis()


if not os.environ.get("DJANGO_SETTINGS_SKIP_LOCAL", False):
    try:
        from .local_settings import *
    except ImportError:
        pass
