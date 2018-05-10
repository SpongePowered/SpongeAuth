import unittest
import re

import django.core.mail
import django.test
import django.shortcuts
import django.http

from . import factories
from .. import forms
from .. import models


class TestRegister(django.test.TestCase):
    def login(self, c, user):
        assert c.login(username=user.username, password='secret')

    def path(self):
        return django.shortcuts.reverse('accounts:register')

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

    def test_constructs_registration_form(self):
        resp = self.client.get(self.path())
        assert isinstance(resp.context['form'], forms.RegisterForm)

    @unittest.mock.patch('accounts.views._send_verify_email')
    def test_invalid_user(self, mock_send_verify_email):
        assert not models.User.objects.all().exists()
        resp = self.client.post(
            self.path(),
            {'username': '', 'password': 'password4363',
             'email': 'baz@example.com', 'accept_tos_1': 'accept_tos_1'})
        assert resp.status_code == 200
        assert not models.User.objects.all().exists()
        mock_send_verify_email.assert_not_called()
        authed_user = django.contrib.auth.get_user(self.client)
        assert not authed_user.is_authenticated

    @unittest.mock.patch('accounts.views._send_verify_email')
    def test_bad_password(self, mock_send_verify_email):
        assert not models.User.objects.all().exists()
        resp = self.client.post(
            self.path(),
            {'username': 'username', 'password': 'username',
             'email': 'baz@example.com', 'accept_tos_1': 'accept_tos_1'})
        assert resp.status_code == 200
        assert not models.User.objects.all().exists()
        mock_send_verify_email.assert_not_called()
        authed_user = django.contrib.auth.get_user(self.client)
        assert not authed_user.is_authenticated

    @unittest.mock.patch('accounts.views._send_verify_email')
    def test_valid_user(self, mock_send_verify_email):
        assert not models.User.objects.all().exists()
        resp = self.client.post(
            self.path(),
            {'username': 'foobar', 'password': 'password4363',
             'email': 'baz@example.com', 'accept_tos_1': 'accept_tos_1'})
        assert resp.status_code == 302

        assert models.User.objects.all().exists()
        user = models.User.objects.get()
        assert user.username == 'foobar'
        assert user.password != 'password4363'
        assert user.check_password('password4363')
        assert user.email == 'baz@example.com'
        assert not user.email_verified

        mock_send_verify_email.assert_called_once()
        args, kwargs = mock_send_verify_email.call_args
        assert len(args) == 2
        assert args[1] == user

        authed_user = django.contrib.auth.get_user(self.client)
        assert authed_user == user

    @django.test.override_settings(REQUIRE_EMAIL_CONFIRM=False)
    @unittest.mock.patch('accounts.views._send_verify_email')
    def test_valid_user_require_email_confirm_disabled(self, mock_send_verify_email):
        assert not models.User.objects.all().exists()
        resp = self.client.post(
            self.path(),
            {'username': 'foobar', 'password': 'password4363',
             'email': 'baz@example.com', 'accept_tos_1': 'accept_tos_1'})
        assert resp.status_code == 302

        assert models.User.objects.all().exists()
        user = models.User.objects.get()
        assert user.username == 'foobar'
        assert user.password != 'password4363'
        assert user.check_password('password4363')
        assert user.email == 'baz@example.com'
        assert not user.email_verified

        mock_send_verify_email.assert_not_called()

        authed_user = django.contrib.auth.get_user(self.client)
        assert authed_user == user

    def test_verify_link_works(self):
        assert not models.User.objects.all().exists()
        resp = self.client.post(
            self.path(),
            {'username': 'foobar', 'password': 'password4363',
             'email': 'baz@example.com', 'accept_tos_1': 'accept_tos_1'})
        assert resp.status_code == 302

        assert len(django.core.mail.outbox) == 1
        email = django.core.mail.outbox[0]
        link_match = re.search(r'^https?:\/\/testserver(\/.*)$', email.body, re.MULTILINE)
        assert link_match
        link = link_match.group(1)

        resp = self.client.get(link)
        assert resp.status_code == 302

    def test_cannot_repeatedly_reuse_token(self):
        assert not models.User.objects.all().exists()
        resp = self.client.post(
            self.path(),
            {'username': 'foobar', 'password': 'password4363',
             'email': 'baz@example.com', 'accept_tos_1': 'accept_tos_1'})
        assert resp.status_code == 302

        assert len(django.core.mail.outbox) == 1
        email = django.core.mail.outbox[0]
        link_match = re.search(r'^https?:\/\/testserver(\/.*)$', email.body, re.MULTILINE)
        assert link_match
        link = link_match.group(1)

        resp = self.client.get(link)
        assert resp.status_code == 302

        user = models.User.objects.get()
        user.email_verified = False
        user.email = 'baz2@example.com'
        user.save()

        resp = self.client.get(link)
        assert resp.status_code == 404

        user = models.User.objects.get()
        assert not user.email_verified


class TestRegisterGoogle(django.test.TestCase):
    def setUp(self):
        patcher = unittest.mock.patch('accounts.views._verify_google_id_token')
        self.mock_verify_google_id_token = patcher.start()
        self.addCleanup(patcher.stop)

    def path(self):
        # hehehe
        return django.shortcuts.reverse('accounts:login')

    def test_initial_load(self):
        self.mock_verify_google_id_token.return_value = ('token', {'sub': '15151'})
        resp = self.client.post(self.path(), {'login_type': 'google'})
        assert 'form' in resp.context

    @unittest.mock.patch('accounts.views._log_user_in')
    def test_taken_username(self, mock_log_user_in):
        user = factories.UserFactory.create()

        self.mock_verify_google_id_token.return_value = ('token', {'sub': '15151'})
        self.client.post(self.path(), {
            'login_type': 'google', 'form_submitted': 'yes',
            'username': user.username, 'email': user.email,
            'password': 'slartibartfast', 'google_id_token': 'baz',
            'accept_tos_1': 'accept_tos_1'})
        mock_log_user_in.assert_not_called()

    @unittest.mock.patch('accounts.views._log_user_in')
    @unittest.mock.patch('accounts.views._send_verify_email')
    def test_successful_registration_email_unverified(self, mock_send_verify_email, mock_log_user_in):
        assert not models.User.objects.exists()
        self.mock_verify_google_id_token.return_value = ('token', {'sub': '15151'})
        mock_log_user_in.return_value = django.http.HttpResponse('hooray')
        resp = self.client.post(self.path(), {
            'login_type': 'google', 'form_submitted': 'yes',
            'username': 'baz', 'email': 'baz@example.org',
            'password': 'slartibartfast', 'google_id_token': 'baz',
            'accept_tos_1': 'accept_tos_1'})
        assert models.User.objects.exists()
        user = models.User.objects.get()
        assert resp == mock_log_user_in.return_value

        mock_send_verify_email.assert_called_once()
        args, kwargs = mock_send_verify_email.call_args
        assert len(args) == 2
        assert args[1] == user

        mock_log_user_in.assert_called_once()
        args, kwargs = mock_log_user_in.call_args
        assert len(args) == 2
        assert args[1] == user
        assert kwargs == {'skip_twofa': True}

    @unittest.mock.patch('accounts.views._log_user_in')
    @unittest.mock.patch('accounts.views._send_verify_email')
    def test_successful_registration_email_verified(self, mock_send_verify_email, mock_log_user_in):
        assert not models.User.objects.exists()
        self.mock_verify_google_id_token.return_value = (
            'token', {'sub': '15151', 'email': 'baz@example.org', 'email_verified': True})
        mock_log_user_in.return_value = django.http.HttpResponse('hooray')
        resp = self.client.post(self.path(), {
            'login_type': 'google', 'form_submitted': 'yes',
            'username': 'baz', 'email': 'baz@evil.example.com',
            'password': 'slartibartfast', 'google_id_token': 'baz',
            'accept_tos_1': 'accept_tos_1'})
        assert models.User.objects.exists()
        user = models.User.objects.get()
        assert resp == mock_log_user_in.return_value

        # user's email should be overwritten
        assert user.email_verified
        assert user.email == 'baz@example.org'

        mock_send_verify_email.assert_not_called()

        mock_log_user_in.assert_called_once()
        args, kwargs = mock_log_user_in.call_args
        assert len(args) == 2
        assert args[1] == user
        assert kwargs == {'skip_twofa': True}

    def test_verify_link_works(self):
        assert not models.User.objects.exists()
        self.mock_verify_google_id_token.return_value = ('token', {'sub': '15151'})
        resp = self.client.post(self.path(), {
            'login_type': 'google', 'form_submitted': 'yes',
            'username': 'baz', 'email': 'baz@example.org',
            'password': 'slartibartfast', 'google_id_token': 'baz',
            'accept_tos_1': 'accept_tos_1'})
        assert models.User.objects.exists()
        user = models.User.objects.get()
        assert not user.email_verified

        assert len(django.core.mail.outbox) == 1
        email = django.core.mail.outbox[0]
        link_match = re.search(r'^https?:\/\/testserver(\/.*)$', email.body, re.MULTILINE)
        assert link_match
        link = link_match.group(1)

        resp = self.client.get(link)
        assert resp.status_code == 302

        user = models.User.objects.get()
        assert user.email_verified
