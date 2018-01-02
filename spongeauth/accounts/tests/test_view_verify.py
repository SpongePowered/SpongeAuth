import django.test
import django.shortcuts
import django.http
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

import unittest.mock

from . import factories
from .. import models


class TestVerify(django.test.TestCase):
    def setUp(self):
        self.user = factories.UserFactory.create(
            email_verified=False)
        self.client = django.test.Client()
        self.login(self.client, self.user)

    def login(self, c, user):
        assert c.login(username=user.username, password='secret')

    def path(self):
        return django.shortcuts.reverse('accounts:verify')

    def test_redirects_if_logged_out(self):
        client = django.test.Client()
        resp = client.get(self.path())
        assert resp.status_code == 302
        assert resp['Location'].startswith(django.shortcuts.reverse('accounts:login'))

    def test_redirects_if_verified(self):
        self.user.email_verified = True
        self.user.save()
        resp = self.client.get(self.path())
        assert resp.status_code == 302
        assert resp['Location'] == '/'

    @unittest.mock.patch('accounts.views._send_verify_email')
    def test_renders_page_if_not_verified(self, mock_send_verify_email):
        resp = self.client.get(self.path())
        assert resp.status_code == 200
        self.assertTemplateUsed(resp, 'accounts/verify/step1.html')
        mock_send_verify_email.assert_not_called()

    @unittest.mock.patch('accounts.views._send_verify_email')
    def test_resends_email_on_post(self, mock_send_verify_email):
        resp = self.client.post(self.path())
        assert resp.status_code == 200
        self.assertTemplateUsed(resp, 'accounts/verify/step1.html')
        mock_send_verify_email.assert_called_once()
        args, kwargs = mock_send_verify_email.call_args
        assert len(args) == 2
        assert args[1] == self.user


class TestVerifyStep2(django.test.TestCase):
    def setUp(self):
        self.user = factories.UserFactory.create(
            email_verified=False)
        self.client = django.test.Client()
        self.login(self.client, self.user)

        patcher = unittest.mock.patch('accounts.views.verify_token_generator')
        self.mock_token_generator = patcher.start()
        self.mock_token_generator.check_token.return_value = True
        self.addCleanup(patcher.stop)

    def login(self, c, user):
        assert c.login(username=user.username, password='secret')

    def path(self, user, token, uidb64=None):
        return django.shortcuts.reverse('accounts:verify-step2', kwargs={
            'uidb64': uidb64 or urlsafe_base64_encode(force_bytes(user.id)).decode('utf8'),
            'token': token})

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
        resp = self.client.get(self.path(None, 'deadbeef-cafe', uidb64='foo'))
        assert resp.status_code == 400

    def test_bad_token(self):
        self.mock_token_generator.check_token.return_value = False
        resp = self.client.get(self.path(self.user, 'deadbeef-cafe'))
        assert resp.status_code == 404

    def test_activates(self):
        resp = self.client.get(self.path(self.user, 'deadbeef-cafe'))
        assert resp.status_code == 302
        user = models.User.objects.get(id=self.user.id)
        assert user.email_verified
