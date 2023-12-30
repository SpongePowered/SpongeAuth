from django.utils import timezone
import django.http
import django.http.response
import django.shortcuts
import django.test

import pytest

import accounts.models

from .. import views
from .. import models


@pytest.mark.django_db
class TestShouldGeneratePaperCodes:
    def test_not_twofa_enabled(self):
        user = accounts.models.User(twofa_enabled=False)
        user.save()
        assert not views._should_generate_paper_codes(user)

    def test_no_paper_device(self):
        user = accounts.models.User(twofa_enabled=True)
        user.save()
        assert views._should_generate_paper_codes(user)

    def test_no_paper_codes_left(self):
        user = accounts.models.User(twofa_enabled=True)
        user.save()
        paper_device = models.PaperDevice(owner=user, activated_at=timezone.now())
        paper_device.save()
        assert views._should_generate_paper_codes(user)

    def test_has_paper_codes(self):
        user = accounts.models.User(twofa_enabled=True)
        user.save()
        paper_device = models.PaperDevice(owner=user)
        paper_device.save()
        paper_device.regenerate()
        paper_device.activated_at = timezone.now()
        paper_device.save()
        assert not views._should_generate_paper_codes(user)


@pytest.mark.django_db
class TestGeneratePaperCodesIfNeeded:
    def setup_method(self):
        self.user = accounts.models.User(twofa_enabled=True)
        self.user.save()

    @staticmethod
    def should_generate(res):
        def _should_generate(user):
            return res

        return _should_generate

    def is_redirect_to(self, resp, dest):
        return isinstance(
            resp, django.http.response.HttpResponseRedirectBase
        ) and resp.url == django.shortcuts.resolve_url(dest)

    def test_does_nothing_if_not_needed(self):
        resp = views._generate_paper_codes_if_needed(
            self.user, redirect_to="/aardvark", should_generate=self.should_generate(False)
        )
        assert self.is_redirect_to(resp, "/aardvark")

    def test_deletes_existing_paper_devices(self):
        old_paper_device = models.PaperDevice(owner=self.user, activated_at=timezone.now())
        old_paper_device.save()
        assert old_paper_device in models.PaperDevice.objects.active_for_user(self.user)
        views._generate_paper_codes_if_needed(
            self.user, redirect_to="/aardvark", should_generate=self.should_generate(True)
        )
        assert old_paper_device not in models.PaperDevice.objects.active_for_user(self.user)

    def test_generates_new_paper_device(self):
        assert not models.PaperDevice.objects.filter(owner=self.user).exists()
        views._generate_paper_codes_if_needed(
            self.user, redirect_to="/aardvark", should_generate=self.should_generate(True)
        )
        assert not models.PaperDevice.objects.active_for_user(self.user).exists()
        assert models.PaperDevice.objects.filter(owner=self.user).exists()


@pytest.mark.django_db
class TestGetVerifyDevice:
    def setup_method(self):
        self.user = accounts.models.User.objects.create_user(
            username="fred", email="fred@example.com", password="secret", twofa_enabled=True
        )
        self.user._test_agree_all_tos()

    def test_works_without_devices(self):
        device, other_devices = views._get_verify_device(self.user, None)
        assert device is None
        assert set(other_devices) == set()

    def test_404s_with_unknown_device(self):
        device = models.PaperDevice(owner=self.user, activated_at=timezone.now())
        device.save()
        device_pk = device.id
        device.delete()

        with pytest.raises(django.http.Http404):
            views._get_verify_device(self.user, device_pk)

    def test_404s_with_inactive_device(self):
        device = models.PaperDevice(owner=self.user)
        device.save()

        with pytest.raises(django.http.Http404):
            views._get_verify_device(self.user, device.id)

    def test_404s_with_someone_elses_device(self):
        other_user = accounts.models.User.objects.create_user(
            username="bob", email="bob@example.com", password="secret"
        )
        other_user._test_agree_all_tos()
        other_user.save()

        device = models.PaperDevice(owner=other_user, activated_at=timezone.now())
        device.save()

        views._get_verify_device(other_user, device.id)
        with pytest.raises(django.http.Http404):
            views._get_verify_device(self.user, device.id)

    def test_returns_active_device_by_id(self):
        device = models.PaperDevice(owner=self.user, activated_at=timezone.now())
        device.save()

        got_device, got_other_devices = views._get_verify_device(self.user, device.id)
        assert got_device == device
        assert set(got_other_devices) == set()

    def test_returns_active_device(self):
        device = models.TOTPDevice(owner=self.user, activated_at=timezone.now(), last_t=0)
        device.save()

        got_device, got_other_devices = views._get_verify_device(self.user, None)
        assert got_device == device
        assert set(got_other_devices) == set()

    def test_returns_other_devices(self):
        device = models.TOTPDevice(owner=self.user, activated_at=timezone.now(), last_t=0)
        device.save()

        other_device = models.PaperDevice(owner=self.user, activated_at=timezone.now())
        other_device.save()

        inactive_device = models.PaperDevice(owner=self.user)
        inactive_device.save()

        deleted_device = models.PaperDevice(owner=self.user, activated_at=timezone.now(), deleted_at=timezone.now())
        deleted_device.save()

        got_device, got_other_devices = views._get_verify_device(self.user, None)
        assert got_device == device
        assert set(got_other_devices) == {other_device}
