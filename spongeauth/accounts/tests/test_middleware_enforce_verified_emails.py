import unittest.mock

from django.conf.urls import url, include
import django.http
import django.test
import django.shortcuts
from django.contrib.auth.models import AnonymousUser

import accounts.tests.factories
from .. import middleware


class TestMustVerify:
    def test_not_logged_in(self):
        assert not middleware.EnforceVerifiedEmails.must_verify(AnonymousUser())

    def test_email_verified(self):
        user = accounts.tests.factories.UserFactory.build()
        assert not middleware.EnforceVerifiedEmails.must_verify(user)

    def test_email_not_verified(self):
        user = accounts.tests.factories.UserFactory.build(
            email_verified=False)
        assert middleware.EnforceVerifiedEmails.must_verify(user)


@django.test.override_settings(ROOT_URLCONF='accounts.tests.test_middleware_enforce_verified_emails')
class TestMayPass(django.test.SimpleTestCase):
    def test_allowed(self):
        assert middleware.EnforceVerifiedEmails.may_pass('/allowed/')

    def test_not_allowed(self):
        assert not middleware.EnforceVerifiedEmails.may_pass('/not-allowed/')

    def test_fourohfour(self):
        assert not middleware.EnforceVerifiedEmails.may_pass('/404/')


@unittest.mock.patch('accounts.middleware.EnforceVerifiedEmails.must_verify')
def test_need_not_verify(mock_must_verify):
    mock_must_verify.return_value = False
    request = unittest.mock.MagicMock()
    get_response = unittest.mock.MagicMock()
    get_response.return_value = object()
    request.user = object()
    request.path = object()
    assert middleware.EnforceVerifiedEmails(get_response)(request) is get_response.return_value


@unittest.mock.patch('accounts.middleware.EnforceVerifiedEmails.must_verify')
@unittest.mock.patch('accounts.middleware.EnforceVerifiedEmails.may_pass')
def test_must_verify_may_pass(mock_may_pass, mock_must_verify):
    mock_must_verify.return_value = True
    mock_may_pass.return_value = True
    request = unittest.mock.MagicMock()
    get_response = unittest.mock.MagicMock()
    get_response.return_value = object()
    request.user = object()
    request.path = object()
    assert middleware.EnforceVerifiedEmails(get_response)(request) is get_response.return_value


@unittest.mock.patch('accounts.middleware.EnforceVerifiedEmails.must_verify')
@unittest.mock.patch('accounts.middleware.EnforceVerifiedEmails.may_pass')
def test_must_verify_may_not_pass(mock_may_pass, mock_must_verify):
    mock_must_verify.return_value = True
    mock_may_pass.return_value = False
    request = unittest.mock.MagicMock()
    get_response = unittest.mock.MagicMock()
    get_response.return_value = object()
    request.user = object()
    request.path = object()
    resp = middleware.EnforceVerifiedEmails(get_response)(request)
    assert resp is not get_response.return_value
    assert isinstance(resp, django.http.HttpResponseRedirect)


def not_decorated_view(request):
    return django.http.HttpResponse('hi')


@middleware.allow_without_verified_email
def decorated_view(request):
    return django.http.HttpResponse('nay')


urlpatterns = [
    url(r'^allowed/$', decorated_view, name='allowed'),
    url(r'^not-allowed/$', not_decorated_view, name='not-allowed'),
    url(r'', include(([url(r'^verify/$', decorated_view, name='verify')], 'accounts'))),
]
