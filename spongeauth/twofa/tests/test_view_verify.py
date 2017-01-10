import unittest.mock

import django.urls
import django.test
import django.contrib.auth
from django.utils import timezone

import pytest

import accounts.models
from .. import models


@pytest.mark.django_db
class TestVerify(django.test.TestCase):
    def setUp(self):
        self.user = accounts.models.User.objects.create_user(
            username='bob', email='bob@secret.com', password='secret',
            email_verified=True)

        self.client = django.test.Client()
        session = self.client.session
        session['twofa_target_user'] = self.user.id
        session.save()

        self.device = None
        self.other_devices = []

        patcher = unittest.mock.patch(
            'twofa.views._get_verify_device', self.patch_get_verify_device)
        patcher.start()
        self.addCleanup(patcher.stop)

    def path(self, device=None):
        kwargs = {}
        if device:
            kwargs['device_id'] = device.id
        return django.shortcuts.reverse('twofa:verify', kwargs=kwargs)

    def patch_get_verify_device(self, user, device_id):
        self.requested_user = user
        self.requested_device_id = device_id
        return self.device, self.other_devices

    def test_redirects_if_logged_in(self):
        accounts.models.User.objects.create_user(
            username='fred', email='fred@secret.com', password='secret',
            email_verified=True)

        client = django.test.Client()
        assert client.login(username='fred', password='secret')
        resp = client.get(self.path())
        assert resp.status_code == 302

    def test_redirects_if_not_from_login(self):
        client = django.test.Client()
        resp = client.get(self.path())
        assert resp.status_code == 302

    def test_logs_in_if_no_twofa_devices(self):
        resp = self.client.get(self.path())
        assert resp.status_code == 302
        user = django.contrib.auth.get_user(self.client)
        assert user.is_authenticated()

    def test_full_login_flow_default_device(self):
        self.device = models.PaperDevice(
            owner=self.user)
        self.device.save()

        used_code = models.PaperCode(
            device=self.device, code='deadbeef',
            used_at=timezone.now())
        used_code.save()

        code = models.PaperCode(
            device=self.device, code='aardvark')
        code.save()

        resp = self.client.get(self.path())
        assert self.requested_user == self.user
        assert self.requested_device_id is None
        assert resp.status_code == 200
        self.assertTemplateUsed(resp, 'twofa/verify/base.html')

        resp = self.client.post(self.path(), {'response': 'deadbeef'})
        assert resp.status_code == 200

        resp = self.client.post(self.path(), {'response': 'aardvark'})
        assert resp.status_code == 302
        assert resp['Location'] == django.urls.reverse('index')

        user = django.contrib.auth.get_user(self.client)
        assert user.is_authenticated()

    def test_full_login_flow_different_device(self):
        self.device = models.PaperDevice(
            owner=self.user)
        self.device.save()

        real_device = models.PaperDevice(
            owner=self.user)
        real_device.save()
        self.other_devices = [real_device]

        code = models.PaperCode(
            device=real_device, code='aardvark')
        code.save()

        resp = self.client.get(self.path())
        assert self.requested_user == self.user
        assert self.requested_device_id is None
        assert resp.status_code == 200
        self.assertTemplateUsed(resp, 'twofa/verify/base.html')
        assert set(resp.context[-1]['other_devices']) == {real_device}

        resp = self.client.post(self.path(), {'response': 'aardvark'})
        assert resp.status_code == 200
        user = django.contrib.auth.get_user(self.client)
        assert not user.is_authenticated()

        self.other_devices = [self.device]
        self.device = real_device

        resp = self.client.get(self.path(real_device))
        assert self.requested_user == self.user
        assert self.requested_device_id == str(real_device.id)
        assert resp.status_code == 200

        resp = self.client.post(self.path(real_device), {'response': 'aardvark'})
        assert resp.status_code == 302
        user = django.contrib.auth.get_user(self.client)
        assert user.is_authenticated()
