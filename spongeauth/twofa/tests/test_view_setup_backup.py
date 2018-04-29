import django.test
from django.utils import timezone

import pytest

import accounts.models
from .. import models


@pytest.mark.django_db
class TestSetupBackup(django.test.TestCase):
    def setUp(self):
        self.user = accounts.models.User.objects.create_user(
            username='fred', email='fred@secret.com', password='secret',
            email_verified=True)
        self.user._test_agree_all_tos()

    def login(self, c):
        assert c.login(username='fred', password='secret')

    def path(self, device=None, device_id=None):
        return django.shortcuts.reverse(
            'twofa:paper-code',
            kwargs={'device_id': device_id or device.id})

    def test_requires_login(self):
        client = django.test.Client()
        resp = client.get(self.path(device_id=1))
        assert resp.status_code == 302

    def test_only_own_devices(self):
        other_user = accounts.models.User()
        other_user.save()
        other_device = models.PaperDevice(
            owner=other_user)
        other_device.save()

        client = django.test.Client()
        self.login(client)
        resp = client.get(self.path(device_id=other_device.pk))
        assert resp.status_code == 404

    def test_forbids_active_device(self):
        active_device = models.PaperDevice(
            owner=self.user,
            activated_at=timezone.now())
        active_device.save()

        client = django.test.Client()
        self.login(client)
        resp = client.get(self.path(device_id=active_device.pk))
        assert resp.status_code == 404

    def test_forbids_deleted_device(self):
        deleted_device = models.PaperDevice(
            owner=self.user,
            deleted_at=timezone.now())
        deleted_device.save()

        client = django.test.Client()
        self.login(client)
        resp = client.get(self.path(device_id=deleted_device.pk))
        assert resp.status_code == 404

    def test_renders_codes(self):
        device = models.PaperDevice(
            owner=self.user)
        device.save()

        models.PaperCode(device=device, code='12345678').save()
        models.PaperCode(device=device, code='1337beef').save()

        client = django.test.Client()
        self.login(client)
        resp = client.get(self.path(device_id=device.pk))
        assert resp.status_code == 200
        assert set(resp.context[-1]['codes']) == {'12345678', '1337beef'}

        assert device not in models.PaperDevice.objects.active_for_user(self.user)

    def test_activates_on_post(self):
        device = models.PaperDevice(
            owner=self.user)
        device.save()

        client = django.test.Client()
        self.login(client)
        resp = client.post(self.path(device_id=device.pk))
        assert resp.status_code == 302

        assert device in models.PaperDevice.objects.active_for_user(self.user)

    def test_redirects_on_post_to_next(self):
        device = models.PaperDevice(
            owner=self.user)
        device.save()

        client = django.test.Client()
        self.login(client)
        resp = client.post(self.path(device_id=device.pk) + '?next=/aardvark')
        assert resp.status_code == 302
        assert resp['Location'] == '/aardvark'

    def test_redirects_on_post_without_next(self):
        device = models.PaperDevice(
            owner=self.user)
        device.save()

        client = django.test.Client()
        self.login(client)
        resp = client.post(self.path(device_id=device.pk))
        assert resp.status_code == 302
        assert resp['Location'] == django.shortcuts.reverse('twofa:list')
