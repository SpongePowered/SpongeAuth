import unittest

import django.test
import django.shortcuts
import django.http

import oauth2client.crypt

from . import factories
from .. import forms
from .. import models


class TestLogin(django.test.TestCase):
    def login(self, c, user):
        assert c.login(username=user.username, password='secret')

    def path(self):
        return django.shortcuts.reverse('accounts:login')

    def test_redirects_onwards_if_logged_in(self):
        user = factories.UserFactory.create()
        self.login(self.client, user)
        resp = self.client.get(self.path() + '?next=/aardvark/')
        assert resp['Location'] == '/aardvark/'

    def test_doesnt_redirect_if_offsite(self):
        user = factories.UserFactory.create()
        self.login(self.client, user)
        resp = self.client.get(self.path() + '?next=https://www.google.com/')
        assert 'google.com' not in resp['Location']

    def test_next_appears_in_template(self):
        resp = self.client.get(self.path() + '?next=/aardvark/')
        assert 'next' in resp.context
        assert resp.context['next'] == '/aardvark/'

    @unittest.mock.patch('accounts.views.login_google')
    def test_invokes_login_google_if_google(self, mock_login_google):
        mock_login_google.return_value = django.http.HttpResponse('ohai')
        resp = self.client.post(self.path(), {'login_type': 'google'})
        mock_login_google.assert_called_once()
        assert resp is mock_login_google.return_value

    def test_constructs_authentication_form(self):
        resp = self.client.get(self.path())
        assert isinstance(resp.context['form'], forms.AuthenticationForm)

    def test_errors_with_invalid_username(self):
        resp = self.client.post(self.path(), {'username': 'foobar', 'password': 'barbarbar'})
        assert isinstance(resp.context['form'], forms.AuthenticationForm)
        self.assertFormError(resp, 'form', 'username', 'There is no user with that username.')
        user = django.contrib.auth.get_user(self.client)
        assert not user.is_authenticated()

    def test_errors_with_invalid_password(self):
        user = factories.UserFactory.create()
        resp = self.client.post(self.path(), {'username': user.username, 'password': 'barbarbar'})
        assert isinstance(resp.context['form'], forms.AuthenticationForm)
        self.assertFormError(resp, 'form', 'password', 'The provided password was incorrect.')
        user = django.contrib.auth.get_user(self.client)
        assert not user.is_authenticated()

    @unittest.mock.patch('accounts.views._log_user_in')
    def test_logs_in_with_valid_password(self, mock_log_user_in):
        mock_log_user_in.return_value = django.http.HttpResponse('yay')
        user = factories.UserFactory.create()
        resp = self.client.post(self.path(), {'username': user.username, 'password': 'secret'})
        assert resp is mock_log_user_in.return_value

        args, kwargs = mock_log_user_in.call_args
        assert args[1] == user


class TestLoginGoogle(django.test.TestCase):
    def setUp(self):
        patcher = unittest.mock.patch('accounts.views._verify_google_id_token')
        self.mock_verify_google_id_token = patcher.start()
        self.addCleanup(patcher.stop)

    def path(self):
        return django.shortcuts.reverse('accounts:login')

    def test_verify_token_fails(self):
        self.mock_verify_google_id_token.side_effect = oauth2client.crypt.AppIdentityError('boo')
        resp = self.client.post(self.path(), {'login_type': 'google'}, follow=True)
        assert len(resp.redirect_chain) == 1
        assert 'An error occurred logging you in. Please try again later.' in [
            m.message for m in resp.context['messages']]

    @unittest.mock.patch('accounts.views._log_user_in')
    def test_has_existing_user(self, mock_log_user_in):
        self.mock_verify_google_id_token.return_value = ('token', {'sub': '15151'})
        mock_log_user_in.return_value = django.http.HttpResponse('yay')
        user = factories.UserFactory.create()
        models.ExternalAuthenticator.objects.create(
            source=models.ExternalAuthenticator.GOOGLE,
            external_id='15151',
            user=user)
        resp = self.client.post(self.path(), {'login_type': 'google'})

        assert resp is mock_log_user_in.return_value
        args, kwargs = mock_log_user_in.call_args
        assert len(args) == 2
        assert args[1] == user
        assert kwargs == {'skip_twofa': True}

    @unittest.mock.patch('accounts.views._log_user_in')
    def test_no_existing_user(self, mock_log_user_in):
        self.mock_verify_google_id_token.return_value = ('token', {'sub': '15151'})
        self.client.post(self.path(), {'login_type': 'google'})
        mock_log_user_in.assert_not_called()
