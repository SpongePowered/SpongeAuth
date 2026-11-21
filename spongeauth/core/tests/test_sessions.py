import django.conf
import django.test

import pytest


@pytest.mark.django_db
def test_unknown_session_cookie_is_anonymous():
    # e.g. a session removed by clearsessions or signed out elsewhere
    client = django.test.Client()
    client.cookies[django.conf.settings.SESSION_COOKIE_NAME] = "doesnotexist0123456789abcdefghij"
    resp = client.get("/admin/")
    assert resp.status_code == 302
    assert resp["Location"] == "/admin/login/?next=/admin/"
