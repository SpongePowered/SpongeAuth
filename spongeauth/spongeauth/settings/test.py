import os

from .base import *

IS_TESTING = True

for queue in RQ_QUEUES.values():
    queue["ASYNC"] = False
from fakeredis import FakeRedis, FakeStrictRedis
import django_rq.connection_utils
import django_rq.queues


def _fake_redis(_config, use_strict_redis=False):
    return FakeStrictRedis() if use_strict_redis else FakeRedis()


# django-rq 4 builds connections in connection_utils, and queues imports the function by name
django_rq.connection_utils.get_redis_connection = _fake_redis
django_rq.queues.get_redis_connection = _fake_redis

if not os.environ.get("DJANGO_SETTINGS_SKIP_LOCAL", False):
    try:
        from .local_settings import *
    except ImportError:
        pass
