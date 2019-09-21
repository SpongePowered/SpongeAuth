import django.test

import pytest

import accounts.tests.factories


def test_admin_login_redirect():
    client = django.test.Client()
    resp = client.get("/admin/", follow=True)
    assert resp.redirect_chain == [("/admin/login/?next=/admin/", 302), ("/accounts/login/?next=%2Fadmin%2F", 302)]


@pytest.mark.django_db
def test_admin_login_redirect_not_staff():
    user = accounts.tests.factories.UserFactory.create()
    client = django.test.Client()
    client.login(username=user.username, password="secret")
    resp = client.get("/admin/", follow=True)
    assert resp.redirect_chain == [("/admin/login/?next=/admin/", 302), ("/", 302)]
