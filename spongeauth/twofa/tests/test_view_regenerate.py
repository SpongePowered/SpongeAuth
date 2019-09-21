import django.test
from django.utils import timezone
import django.core.signing

import pytest

import accounts.models
from .. import models


@pytest.mark.django_db
class TestRegenerate(django.test.TestCase):
    def setUp(self):
        self.user = accounts.models.User.objects.create_user(
            username="fred", email="fred@secret.com", password="secret", email_verified=True, twofa_enabled=True
        )
        self.user._test_agree_all_tos()

        self.dead_backup_device = models.PaperDevice(
            owner=self.user, activated_at=timezone.now(), deleted_at=timezone.now()
        )
        self.dead_backup_device.save()

        self.backup_device = models.PaperDevice(owner=self.user, activated_at=timezone.now())
        self.backup_device.save()

        self.totp_device = models.TOTPDevice(owner=self.user, activated_at=timezone.now(), last_t=0)
        self.totp_device.save()

        self.client = django.test.Client()
        self.login(self.client)

    def login(self, c, username="fred"):
        assert c.login(username=username, password="secret")

    def path(self, device_id=None, device=None):
        return django.shortcuts.reverse("twofa:regenerate", kwargs={"device_id": device_id or device.id})

    def test_requires_login(self):
        client = django.test.Client()
        resp = client.get(self.path(device_id=1))
        assert resp.status_code == 302

    def test_rejects_get(self):
        resp = self.client.get(self.path(device=self.backup_device))
        assert resp.status_code == 405

    def test_regenerate_someone_elses_device(self):
        bob = accounts.models.User.objects.create_user(
            username="bob", email="bob@secret.com", password="secret", email_verified=True
        )
        bob._test_agree_all_tos()
        self.login(self.client, username="bob")

        resp = self.client.post(self.path(device=self.backup_device))
        assert resp.status_code == 404

    def test_regenerate_deleted_device(self):
        resp = self.client.post(self.path(device=self.dead_backup_device))
        assert resp.status_code == 404

    def test_regenerate_unregeneratable_device(self):
        resp = self.client.post(self.path(device=self.totp_device))
        assert resp.status_code == 302

    def test_happy_path(self):
        assert not models.PaperCode.objects.exists()
        resp = self.client.post(self.path(device=self.backup_device))
        assert resp.status_code == 302
        assert models.PaperCode.objects.exists()
