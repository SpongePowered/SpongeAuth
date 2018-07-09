import base64

import django.core.signing
import django.shortcuts
import django.test
from django.utils import timezone

import pytest

import accounts.models
from .. import models
from .. import oath


@pytest.mark.django_db
class TestSetupTotp(django.test.TestCase):
    def setUp(self):
        self.user = accounts.models.User.objects.create_user(
            username='fred', email='fred@secret.com', password='secret',
            email_verified=True)
        self.user._test_agree_all_tos()

        self.client = django.test.Client()
        self.login(self.client)

    def login(self, c):
        assert c.login(username='fred', password='secret')

    def path(self):
        return django.shortcuts.reverse('twofa:setup-totp')

    def extract_secret(self, resp, user=None):
        setup_signer = self.signer(user or self.user)
        return base64.b32decode(setup_signer.unsign(resp.context[-1]['form'].secret))

    def signer(self, user):
        return django.core.signing.TimestampSigner('twofa.views.setup_totp:{}'.format(user.pk))

    def test_requires_login(self):
        client = django.test.Client()
        resp = client.get(self.path())
        assert resp.status_code == 302

    def test_disallows_multiple_totp(self):
        existing_device = models.TOTPDevice(
            owner=self.user, last_t=0,
            activated_at=timezone.now())
        existing_device.save()

        resp = self.client.get(self.path())
        assert resp.status_code == 302

    def test_allows_totp_if_previous_disabled(self):
        existing_device = models.TOTPDevice(
            owner=self.user, last_t=0,
            activated_at=timezone.now(),
            deleted_at=timezone.now())
        existing_device.save()

        resp = self.client.get(self.path())
        assert resp.status_code == 200

    def test_activation_flow(self):
        resp = self.client.get(self.path())
        assert resp.status_code == 200

        secret = self.extract_secret(resp)
        form = resp.context[-1]['form']
        totp = oath.TOTP(secret)
        invalid_token = totp.token() + 1
        resp = self.client.post(self.path(), {'secret': form.secret, 'response': invalid_token})
        assert resp.status_code == 200
        assert not models.TOTPDevice.objects.active_for_user(self.user).exists()

        valid_token = totp.token()
        resp = self.client.post(self.path(), {'secret': form.secret, 'response': valid_token})
        assert resp.status_code == 302
        assert models.TOTPDevice.objects.active_for_user(self.user).exists()

    def test_expired_secret(self):
        signer = self.signer(self.user)
        signer.timestamp = lambda: 0
        expired_token = signer.sign('foobar')

        resp = self.client.post(self.path(), {'secret': expired_token, 'response': '123123'})
        assert resp.status_code == 302
        assert resp['Location'] == self.path()

    def test_invalid_secret(self):
        invalid_token = 'garbage:g'

        resp = self.client.post(self.path(), {'secret': invalid_token, 'response': '123123'})
        assert resp.status_code == 302
        assert resp['Location'] == self.path()

    def test_someone_elses_token(self):
        bob_user = accounts.models.User.objects.create_user(
            username='bob', email='bob@secret.com', password='secret',
            email_verified=True)
        bob_user._test_agree_all_tos()

        someone_elses_token = self.signer(bob_user).sign('foobar')
        resp = self.client.post(self.path(), {'secret': someone_elses_token, 'response': '123123'})
        assert resp.status_code == 302
        assert resp['Location'] == self.path()
