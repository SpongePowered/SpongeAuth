import django.test
from django.utils import timezone
import django.core.signing

import pytest

import accounts.models
from .. import models


@pytest.mark.django_db
class TestList(django.test.TestCase):
    def setUp(self):
        self.user = accounts.models.User.objects.create_user(
            username='fred', email='fred@secret.com', password='secret',
            email_verified=True, twofa_enabled=True)
        self.other_user = accounts.models.User.objects.create_user(
            username='bob', email='bob@secret.com', password='secret',
            email_verified=True, twofa_enabled=True)

        self.dead_backup_device = models.PaperDevice(
            owner=self.user, activated_at=timezone.now(),
            deleted_at=timezone.now())
        self.dead_backup_device.save()

        self.backup_device = models.PaperDevice(
            owner=self.user, activated_at=timezone.now())
        self.backup_device.save()

        self.totp_device = models.TOTPDevice(
            owner=self.user, activated_at=timezone.now(),
            last_t=0)
        self.totp_device.save()

        self.bobs_totp_device = models.TOTPDevice(
            owner=self.other_user, activated_at=timezone.now(),
            last_t=0)
        self.bobs_totp_device.save()

        self.client = django.test.Client()
        self.login(self.client)

    def login(self, c, username='fred'):
        assert c.login(username=username, password='secret')

    def path(self):
        return django.shortcuts.reverse('twofa:list')

    def test_requires_login(self):
        client = django.test.Client()
        resp = client.get(self.path())
        assert resp.status_code == 302

    def test_lists(self):
        resp = self.client.get(self.path())
        assert resp.status_code == 200
        assert set(resp.context[-1]['devices']) == {self.totp_device, self.backup_device}
