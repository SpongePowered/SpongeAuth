import os

from .base import *

IS_TESTING = True

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
