import django.test
import django.shortcuts
import django.http
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

import unittest.mock

from . import factories
from .. import models


class TestChangeEmail(django.test.TestCase):
    def setUp(self):
        self.user = factories.UserFactory.create(
            email_verified=False)
        self.client = django.test.Client()
        self.login(self.client, self.user)

    def login(self, c, user):
        assert c.login(username=user.username, password='secret')

    def path(self):
        return django.shortcuts.reverse('accounts:change-email')

    def test_redirects_if_logged_out(self):
        client = django.test.Client()
        resp = client.get(self.path())
        assert resp.status_code == 302
        assert resp['Location'].startswith(django.shortcuts.reverse('accounts:login'))

    @unittest.mock.patch('accounts.views._send_change_email')
    def test_renders_page_if_unverified(self, mock_send_change_email):
        resp = self.client.get(self.path())
        assert resp.status_code == 200
        self.assertTemplateUsed(resp, 'accounts/change_email/step1.html')
        mock_send_change_email.assert_not_called()

    @unittest.mock.patch('accounts.views._send_change_email')
    def test_renders_page_if_verified(self, mock_send_change_email):
        self.user.email_verified = True
        self.user.save()
        resp = self.client.get(self.path())
        assert resp.status_code == 200
        self.assertTemplateUsed(resp, 'accounts/change_email/step1.html')
        mock_send_change_email.assert_not_called()

    @unittest.mock.patch('accounts.views._send_change_email')
    def test_fails_if_same_email(self, mock_send_change_email):
        resp = self.client.post(self.path(), {'new_email': self.user.email})
        assert resp.status_code == 200
        self.assertTemplateUsed(resp, 'accounts/change_email/step1.html')
        mock_send_change_email.assert_not_called()

    @unittest.mock.patch('accounts.views._send_change_email')
    def test_kicks_off_change(self, mock_send_change_email):
        resp = self.client.post(self.path(), {'new_email': 'deadbeef2@example.com'}, follow=True)
        assert resp.status_code == 200
        assert 'deadbeef2@example.com'.encode('utf8') in resp.content
        assert len(resp.redirect_chain) == 1
        self.assertTemplateUsed(resp, 'accounts/change_email/step1done.html')

        mock_send_change_email.assert_called_once()
        args, kwargs = mock_send_change_email.call_args
        assert len(args) == 3
        assert args[1] == self.user
        assert args[2] == 'deadbeef2@example.com'


class TestChangeEmailStep1Done(django.test.TestCase):
    def setUp(self):
        self.user = factories.UserFactory.create(
            email_verified=False)
        self.client = django.test.Client()
        self.login(self.client, self.user)

    def login(self, c, user):
        assert c.login(username=user.username, password='secret')

    def path(self, e=None):
        path = django.shortcuts.reverse('accounts:change-email-sent')
        if e:
            path += '?e=' + urlsafe_base64_encode(e.encode('utf8')).decode('utf8')
        return path

    def test_redirects_if_logged_out(self):
        client = django.test.Client()
        resp = client.get(self.path('asdf'))
        assert resp.status_code == 302
        assert resp['Location'].startswith(django.shortcuts.reverse('accounts:login'))

    @unittest.mock.patch('accounts.views.Signer')
    def test_valid_signature(self, mock_signer):
        mock_signer.return_value.unsign.return_value = 'foo@example.org'
        resp = self.client.get(self.path())
        mock_signer.assert_called_once()
        assert resp.status_code == 200
        assert b'foo@example.org' in resp.content

    @unittest.mock.patch('accounts.views.Signer')
    def test_invalid_signature(self, mock_signer):
        mock_signer.return_value.unsign.side_effect = django.core.signing.BadSignature('failed')
        resp = self.client.get(self.path())
        mock_signer.assert_called_once()
        assert resp.status_code == 400


class TestChangeEmailStep2(django.test.TestCase):
    def setUp(self):
        self.user = factories.UserFactory.create(
            email_verified=False)
        self.client = django.test.Client()
        self.login(self.client, self.user)

        patcher = unittest.mock.patch('accounts.views.verify_token_generator')
        self.mock_token_generator = patcher.start()
        self.mock_token_generator.check_token.return_value = True
        self.addCleanup(patcher.stop)

        patcher = unittest.mock.patch('accounts.views._send_email_changed_email')
        self.mock_email_changed_email = patcher.start()
        self.addCleanup(patcher.stop)

    def login(self, c, user):
        assert c.login(username=user.username, password='secret')

    def path(self, user, token, uidb64=None, new_email=None):
        return django.shortcuts.reverse('accounts:change-email-step2', kwargs={
            'uidb64': uidb64 or urlsafe_base64_encode(force_bytes(user.id)).decode('utf8'),
            'token': token,
            'new_email': new_email or urlsafe_base64_encode(force_bytes(user.email)).decode('utf8')})

    def test_redirects_if_logged_out(self):
        client = django.test.Client()
        resp = client.get(self.path(self.user, 'deadbeef-cafe'))
        assert resp.status_code == 302
        assert resp['Location'].startswith(django.shortcuts.reverse('accounts:login'))

    def test_redirects_if_verified(self):
        self.user.email_verified = True
        self.user.save()
        resp = self.client.get(self.path(self.user, 'deadbeef-cafe'))
        assert resp.status_code == 302
        assert resp['Location'] == '/'

    def test_errors_if_someone_else(self):
        other_user = factories.UserFactory.create()
        resp = self.client.get(self.path(other_user, 'deadbeef-cafe'))
        assert resp.status_code == 403

    def test_bad_user_id(self):
        resp = self.client.get(self.path(None, 'deadbeef-cafe', uidb64='foo',
                                         new_email=urlsafe_base64_encode(b'a@example.com').decode('utf8')))
        assert resp.status_code == 400

    def test_bad_token(self):
        self.mock_token_generator.check_token.return_value = False
        resp = self.client.get(self.path(self.user, 'deadbeef-cafe'))
        assert resp.status_code == 404

    def test_activates_if_not_active(self):
        assert not self.user.email_verified
        resp = self.client.get(self.path(self.user, 'deadbeef-cafe',
                                         new_email=urlsafe_base64_encode(b'a@example.com').decode('utf8')))
        assert resp.status_code == 302
        user = models.User.objects.get(id=self.user.id)
        assert user.email_verified
        assert user.email == 'a@example.com'
        self.mock_email_changed_email.assert_not_called()

    def test_changes_email_if_active(self):
        self.user.email_verified = True
        self.user.save()
        resp = self.client.get(self.path(self.user, 'deadbeef-cafe',
                                         new_email=urlsafe_base64_encode(b'a@example.com').decode('utf8')))
        assert resp.status_code == 302
        user = models.User.objects.get(id=self.user.id)
        assert user.email_verified
        self.mock_email_changed_email.assert_called_once()
