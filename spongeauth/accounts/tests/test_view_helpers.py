import unittest.mock

import django.test
import django.test.client
import django.shortcuts
from django.contrib.sessions.middleware import SessionMiddleware

import pytest
import oauth2client.crypt

from . import factories
from .. import views


def _make_request(path):
    request = django.test.client.RequestFactory().get(path)
    request = SessionMiddleware(lambda request: request)(request)
    return request


class TestLogUserIn:
    @unittest.mock.patch('django.contrib.auth.login')
    def test_default_flow(self, mock_login):
        user = factories.UserFactory.build()
        request = unittest.mock.MagicMock()
        request.POST = {'next': '/'}
        response = views._log_user_in(request, user)
        mock_login.assert_called_once_with(request, user)
        assert response['Location'] == '/'

    @unittest.mock.patch('django.contrib.auth.login')
    def test_unsafe_next(self, mock_login):
        user = factories.UserFactory.build()
        request = unittest.mock.MagicMock()
        request.POST = {'next': 'https://www.google.co.uk'}
        response = views._log_user_in(request, user)
        mock_login.assert_called_once_with(request, user)
        assert response['Location'] != 'https://www.google.co.uk'

    @unittest.mock.patch('django.contrib.auth.login')
    def test_twofa_enabled(self, mock_login):
        user = factories.UserFactory.build(twofa_enabled=True)
        request = unittest.mock.MagicMock()
        response = views._log_user_in(request, user)
        mock_login.assert_not_called()
        assert response['Location'].startswith(
            django.shortcuts.reverse('twofa:verify'))

    @unittest.mock.patch('django.contrib.auth.login')
    def test_twofa_enabled_but_skipped(self, mock_login):
        user = factories.UserFactory.build(twofa_enabled=True)
        request = unittest.mock.MagicMock()
        response = views._log_user_in(request, user, skip_twofa=True)
        mock_login.assert_called_once_with(request, user)
        assert response['Location'] == '/'


class TestLoginRedirectURL:
    def test_next_from_post(self):
        request = unittest.mock.MagicMock()
        request.POST = {'next': '/foobar/'}
        request.GET = {'next': '/foo/'}
        assert views._login_redirect_url(request) == '/foobar/'

    def test_next_from_get(self):
        request = unittest.mock.MagicMock()
        request.POST = {}
        request.GET = {'next': '/foo/'}
        assert views._login_redirect_url(request) == '/foo/'

    @django.test.override_settings(LOGIN_REDIRECT_URL='/login/done/')
    def test_next_fallback(self):
        request = unittest.mock.MagicMock()
        assert views._login_redirect_url(request) == '/login/done/'

    def test_next_override_fallback(self):
        request = unittest.mock.MagicMock()
        assert views._login_redirect_url(request, '/override/') == '/override/'

    @django.test.override_settings(LOGIN_REDIRECT_URL='/login/done/')
    def test_next_unsafe_from_post(self):
        request = unittest.mock.MagicMock()
        request.POST = {'next': 'https://www.google.co.uk/'}
        request.GET = {'next': '/foo/'}
        assert views._login_redirect_url(request) == '/login/done/'

    @django.test.override_settings(LOGIN_REDIRECT_URL='/login/done/')
    def test_next_unsafe_from_get(self):
        request = unittest.mock.MagicMock()
        request.POST = {}
        request.GET = {'next': 'https://www.google.co.uk'}
        assert views._login_redirect_url(request) == '/login/done/'


class TestObfuscateError(django.test.SimpleTestCase):
    @django.test.override_settings(DEBUG=False)
    def test_production(self):
        assert 'slartibartfast' not in views._obfuscate_error('slartibartfast')

    @django.test.override_settings(DEBUG=True)
    def test_development(self):
        assert views._obfuscate_error('slartibartfast') == 'slartibartfast'


class TestBuildGoogleRegisterForm:
    @unittest.mock.patch('accounts.forms.RegisterGoogleForm')
    def test_initial_load(self, mock_register_form):
        request = unittest.mock.MagicMock()
        request.method = 'GET'
        id_token = 'passed through'
        idinfo = {'email': 'foo@example.com', 'name': 'Foo Bar', 'email_verified': False}
        mock_register_form.return_value = object()
        form = views._build_google_register_form(request, id_token, idinfo)
        mock_register_form.assert_called_once_with(email_editable=True, initial={
            'email': 'foo@example.com',
            'username': 'Foo_Bar',
            'google_id_token': id_token})
        assert form is mock_register_form.return_value

    @unittest.mock.patch('accounts.forms.RegisterGoogleForm')
    def test_email_verified(self, mock_register_form):
        request = unittest.mock.MagicMock()
        request.method = 'GET'
        id_token = 'passed through'
        idinfo = {'email': 'foo@example.com', 'name': 'Foo Bar', 'email_verified': True}
        mock_register_form.return_value = object()
        form = views._build_google_register_form(request, id_token, idinfo)
        mock_register_form.assert_called_once_with(email_editable=False, initial={
            'email': 'foo@example.com',
            'username': 'Foo_Bar',
            'google_id_token': id_token})
        assert form is mock_register_form.return_value

    @unittest.mock.patch('accounts.forms.RegisterGoogleForm')
    def test_initial_load_via_post(self, mock_register_form):
        request = unittest.mock.MagicMock()
        request.POST = {'username': 'Not_Overridden'}
        request.method = 'POST'
        id_token = 'passed through'
        idinfo = {'email': 'foo@example.com', 'name': 'Foo Bar', 'email_verified': False}
        mock_register_form.return_value = object()
        form = views._build_google_register_form(request, id_token, idinfo)
        mock_register_form.assert_called_once_with(email_editable=True, initial={
            'email': 'foo@example.com',
            'username': 'Foo_Bar',
            'google_id_token': id_token})
        assert form is mock_register_form.return_value

    @unittest.mock.patch('accounts.forms.RegisterGoogleForm')
    def test_subsequent_load(self, mock_register_form):
        request = unittest.mock.MagicMock()
        request.POST = {'username': 'Overridden', 'form_submitted': 'yes'}
        request.method = 'POST'
        id_token = 'passed through'
        idinfo = {'email': 'foo@example.com', 'name': 'Foo Bar', 'email_verified': False}
        mock_register_form.return_value = object()
        form = views._build_google_register_form(request, id_token, idinfo)
        mock_register_form.assert_called_with(
            request.POST,
            email_editable=True, initial={
                'email': 'foo@example.com',
                'username': 'Foo_Bar',
                'google_id_token': id_token})
        assert form is mock_register_form.return_value


class TestVerifyGoogleIDToken:
    def test_no_id_token(self):
        request = unittest.mock.MagicMock()
        request.POST = {}
        with pytest.raises(oauth2client.crypt.AppIdentityError) as exc:
            views._verify_google_id_token(request)
        assert 'google_id_token' in str(exc.value)

    @unittest.mock.patch('oauth2client.client.verify_id_token')
    @django.test.override_settings(GOOGLE_CLIENT_ID='gcid')
    def test_invalid_issuer(self, mock_verify_id_token):
        mock_verify_id_token.return_value = {'iss': 'invalid.foo.com'}
        request = unittest.mock.MagicMock()
        request.POST = {'google_id_token': 'baz'}
        with pytest.raises(oauth2client.crypt.AppIdentityError) as exc:
            views._verify_google_id_token(request)
        assert str(exc.value) == 'Invalid issuer.'
        assert mock_verify_id_token.called_once_with('baz', 'gcid')

    @unittest.mock.patch('oauth2client.client.verify_id_token')
    @django.test.override_settings(GOOGLE_CLIENT_ID='gcid')
    def test_valid_token(self, mock_verify_id_token):
        mock_verify_id_token.return_value = {'iss': 'accounts.google.com'}
        request = unittest.mock.MagicMock()
        request.POST = {'google_id_token': 'baz'}
        got_token, got_idinfo = views._verify_google_id_token(request)
        assert got_token == 'baz'
        assert got_idinfo == mock_verify_id_token.return_value


@unittest.mock.patch('accounts.views.render_to_string')
@unittest.mock.patch('accounts.views.send_mail')
@unittest.mock.patch('accounts.views.verify_token_generator')
def test_send_verify_email(mock_token_generator, mock_send_mail, mock_render_to_string):
    mock_render_to_string.side_effect = lambda template, kwargs: template
    mock_token_generator.make_token.return_value = 'deadbeef-cafe'
    request = unittest.mock.MagicMock()
    request.build_absolute_uri.side_effect = lambda inp: inp
    user = factories.UserFactory.build()
    views._send_verify_email(request, user)
    mock_send_mail.assert_called_once_with(
        '[Sponge] Confirm your email address',
        'accounts/verify/email.txt',
        'admin@spongepowered.org',
        [user.email],
        html_message='accounts/verify/email.html')
    template_kwargs = {
        'user': user,
        'link': '/accounts/verify/Tm9uZQ/deadbeef-cafe/'
    }
    mock_render_to_string.assert_any_call(
        'accounts/verify/email.html', template_kwargs)
    mock_render_to_string.assert_any_call(
        'accounts/verify/email.txt', template_kwargs)


@unittest.mock.patch('accounts.views.render_to_string')
@unittest.mock.patch('accounts.views.send_mail')
@unittest.mock.patch('accounts.views.forgot_token_generator')
def test_send_forgot_email(mock_token_generator, mock_send_mail, mock_render_to_string):
    mock_render_to_string.side_effect = lambda template, kwargs: template
    mock_token_generator.make_token.return_value = 'deadbeef-cafe'
    request = unittest.mock.MagicMock()
    request.META = {'REMOTE_ADDR': '::1'}
    request.build_absolute_uri.side_effect = lambda inp: inp
    user = factories.UserFactory.build()
    views._send_forgot_email(request, user)
    mock_send_mail.assert_called_once_with(
        '[Sponge] Reset your password',
        'accounts/forgot/email.txt',
        'admin@spongepowered.org',
        [user.email],
        html_message='accounts/forgot/email.html')
    template_kwargs = {
        'user': user,
        'ip': '::1',
        'link': '/accounts/reset/Tm9uZQ/deadbeef-cafe/'
    }
    mock_render_to_string.assert_any_call(
        'accounts/forgot/email.html', template_kwargs)
    mock_render_to_string.assert_any_call(
        'accounts/forgot/email.txt', template_kwargs)


@unittest.mock.patch('accounts.views.render_to_string')
@unittest.mock.patch('accounts.views.send_mail')
@unittest.mock.patch('accounts.views.verify_token_generator')
def test_send_change_email(mock_token_generator, mock_send_mail, mock_render_to_string):
    mock_render_to_string.side_effect = lambda template, kwargs: template
    mock_token_generator.make_token.return_value = 'deadbeef-cafe'
    request = unittest.mock.MagicMock()
    request.META = {'REMOTE_ADDR': '::1'}
    request.build_absolute_uri.side_effect = lambda inp: inp
    user = factories.UserFactory.build()
    views._send_change_email(request, user, 'new-email@example.com')
    mock_send_mail.assert_called_once_with(
        '[Sponge] Confirm your new email address',
        'accounts/change_email/email.txt',
        'admin@spongepowered.org',
        ['new-email@example.com'],
        html_message='accounts/change_email/email.html')
    template_kwargs = {
        'user': user,
        'link': '/accounts/change-email/Tm9uZQ/deadbeef-cafe/bmV3LWVtYWlsQGV4YW1wbGUuY29t/'
    }
    mock_render_to_string.assert_any_call(
        'accounts/change_email/email.html', template_kwargs)
    mock_render_to_string.assert_any_call(
        'accounts/change_email/email.txt', template_kwargs)


@unittest.mock.patch('accounts.views.render_to_string')
@unittest.mock.patch('accounts.views.send_mail')
def test_send_email_changed_email(mock_send_mail, mock_render_to_string):
    mock_render_to_string.side_effect = lambda template, kwargs: template
    request = unittest.mock.MagicMock()
    request.build_absolute_uri.side_effect = lambda inp: inp
    user = factories.UserFactory.build()
    views._send_email_changed_email(request, user, 'old-email@example.com')
    mock_send_mail.assert_called_once_with(
        '[Sponge] Your email address has been changed',
        'accounts/change_email/confirmation_email.txt',
        'admin@spongepowered.org',
        ['old-email@example.com'],
        html_message='accounts/change_email/confirmation_email.html')
    template_kwargs = {
        'user': user,
        'new_email': user.email,
    }
    mock_render_to_string.assert_any_call(
        'accounts/change_email/confirmation_email.html', template_kwargs)
    mock_render_to_string.assert_any_call(
        'accounts/change_email/confirmation_email.txt', template_kwargs)


def test_make_gravatar_url():
    user = unittest.mock.MagicMock()
    user.email = '  FooBar@eXaMple.com '
    assert views._make_gravatar_url(user) == 'https://www.gravatar.com/avatar/0d4907cea9d97688aa7a5e722d742f71'
