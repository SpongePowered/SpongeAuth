import secrets

from django.db import models
from django.utils.translation import ugettext as _
from django.utils.translation import ungettext
from django.utils import timezone

from model_utils.managers import InheritanceQuerySet, InheritanceManager

from accounts.models import User

from . import forms


class DeviceQuerySetMixin(object):
    def active_for_user(self, user):
        return self.filter(owner=user, deleted_at=None).exclude(activated_at=None)

    def best_authenticator(self):
        return self.exclude_backup().order_by("last_used_at").first()

    def exclude_backup(self):
        return self.exclude(id__in=PaperDevice.objects.filter(id__in=self))


class PlainDeviceQuerySet(DeviceQuerySetMixin, models.QuerySet):
    pass


class DeviceQuerySet(DeviceQuerySetMixin, InheritanceQuerySet):
    pass


class DeviceManager(InheritanceManager.from_queryset(DeviceQuerySet)):
    def get_queryset(self):
        return DeviceQuerySet(self.model)


class Device(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="twofa_totp_devices")
    added_at = models.DateTimeField(auto_now_add=True, null=False, blank=False)
    last_used_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = DeviceManager()

    def name(self):  # pragma: no cover
        raise NotImplementedError

    def extra_info(self):
        return None

    def verify_form(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def verify_template(self):  # pragma: no cover
        raise NotImplementedError

    def can_delete(self):
        return False

    def can_regenerate(self):
        return False


class TOTPDevice(Device):
    base32_secret = models.CharField(null=False, blank=False, max_length=32)

    # anti-replay protection
    last_t = models.PositiveIntegerField(null=False)

    drift = models.IntegerField(null=False, default=0)

    objects = models.Manager.from_queryset(PlainDeviceQuerySet)()

    def name(self):
        return _("Google Authenticator (TOTP)")

    def verify_form(self, *args, **kwargs):
        kwargs["device"] = self
        return forms.TOTPVerifyForm(*args, **kwargs)

    def verify_template(self):
        return "twofa/verify/totp.html"

    def can_delete(self):
        return True


class PaperDevice(Device):

    objects = models.Manager.from_queryset(PlainDeviceQuerySet)()

    def name(self):
        return _("Backup Codes")

    def extra_info(self):
        count = self.codes.filter(used_at=None).count()
        return ungettext("%(count)d code remaining", "%(count)d codes remaining", count) % {"count": count}

    def verify_form(self, *args, **kwargs):
        kwargs["device"] = self
        return forms.PaperVerifyForm(*args, **kwargs)

    def verify_template(self):
        return "twofa/verify/paper.html"

    def can_regenerate(self):
        return True

    def regenerate(self):
        self.activated_at = None
        self.codes.all().update(used_at=timezone.now())
        self.save()
        for n in range(10):
            code = PaperCode(device=self, code=secrets.token_hex(4))
            code.save()


class PaperCode(models.Model):
    device = models.ForeignKey(PaperDevice, on_delete=models.CASCADE, related_name="codes")

    code = models.CharField(max_length=8, blank=False, null=False)
    used_at = models.DateTimeField(null=True, blank=True)
