import base64
import io
import secrets

from django.urls import reverse
from django.utils.translation import gettext as _
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
import django.contrib.auth
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.http import urlquote, urlencode

import qrcode
import qrcode.image.svg

from accounts.views import _login_redirect_url
import accounts.models
import twofa.models


def _should_generate_paper_codes(user):
    if not user.twofa_enabled:
        return False

    paper_devices = twofa.models.PaperDevice.objects.active_for_user(user)
    if not paper_devices.exists():
        return True

    paper_codes = twofa.models.PaperCode.objects.filter(used_at=None, device__in=paper_devices)
    return not paper_codes.exists()


def _generate_paper_codes_if_needed(user, redirect_to=None, should_generate=_should_generate_paper_codes):
    if not should_generate(user):
        return redirect(redirect_to)

    twofa.models.PaperDevice.objects.active_for_user(user).update(deleted_at=timezone.now())

    device = twofa.models.PaperDevice(owner=user)
    device.regenerate()

    return redirect(
        "{}?{}".format(reverse("twofa:paper-code", kwargs={"device_id": device.pk}), urlencode({"next": redirect_to}))
    )


@login_required
def setup_backup(request, device_id):
    device = get_object_or_404(
        twofa.models.PaperDevice, owner=request.user, deleted_at=None, activated_at=None, pk=device_id
    )
    if request.method == "POST":
        # activate
        device.activated_at = timezone.now()
        device.save()

        return redirect(_login_redirect_url(request, fallback_to=reverse("twofa:list")))

    codes = device.codes.filter(used_at=None).values_list("code", flat=True)
    return render(request, "twofa/setup/paper.html", {"codes": codes})


def _get_verify_device(user, device_id):
    device_qs = twofa.models.Device.objects.active_for_user(user).select_subclasses()
    if device_id:
        device = get_object_or_404(device_qs, pk=device_id)
    else:
        device = device_qs.best_authenticator()
    other_device_qs = []
    if device:
        other_device_qs = device_qs.exclude(pk=device.pk).select_subclasses()
    return device, other_device_qs


def verify(request, device_id=None):
    if request.user.is_authenticated:
        return redirect(_login_redirect_url(request))
    if "twofa_target_user" not in request.session:
        return redirect(_login_redirect_url(request))

    user = get_object_or_404(accounts.models.User, pk=request.session["twofa_target_user"])

    device, other_devices = _get_verify_device(user, device_id)
    if not device:
        # no 2FA devices, just log them in
        django.contrib.auth.login(request, user)
        return redirect(_login_redirect_url(request))

    form = device.verify_form()
    if request.method == "POST":
        form = device.verify_form(request.POST)

        if form.is_valid():
            # now we can actually authenticate the user
            django.contrib.auth.login(request, user)
            return _generate_paper_codes_if_needed(user, _login_redirect_url(request))

    return render(request, device.verify_template(), {"form": form, "other_devices": other_devices})


@login_required
def setup_totp(request):
    if twofa.models.TOTPDevice.objects.active_for_user(request.user).exists():
        messages.error(request, _("You may not have multiple Google Authenticators attached to your account."))
        return redirect("twofa:list")

    setup_signer = TimestampSigner("twofa.views.setup_totp:{}".format(request.user.pk))

    if request.method == "POST" and "secret" in request.POST:
        try:
            b32_secret = setup_signer.unsign(request.POST["secret"], max_age=600)
        except SignatureExpired:
            messages.error(request, _("That took too long and your challenge expired. Here's a new one."))
            return redirect("twofa:setup-totp")
        except BadSignature:
            messages.error(request, _("Whoops - something went wrong. Please try again."))
            return redirect("twofa:setup-totp")
    else:
        b32_secret = base64.b32encode(secrets.token_bytes(10)).decode("utf8")
    signed_secret = setup_signer.sign(b32_secret)

    url = "otpauth://totp/Sponge:{}?{}".format(
        urlquote(request.user.username), urlencode({"secret": b32_secret, "issuer": "Sponge"})
    )
    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathFillImage)
    img_buf = io.BytesIO()
    img.save(img_buf)

    device = twofa.models.TOTPDevice(base32_secret=b32_secret, owner=request.user)
    device.activated_at = timezone.now()  # this won't be saved unless the form is valid
    form = device.verify_form(secret=signed_secret)
    if request.method == "POST":
        form = device.verify_form(request.POST, secret=signed_secret)

        if form.is_valid():
            # relying on verify_form to save the new device
            request.user.twofa_enabled = True
            request.user.save()

            messages.success(request, _("Your authenticator has been added to your account."))
            return _generate_paper_codes_if_needed(request.user, reverse("twofa:list"))

    return render(
        request,
        "twofa/setup/totp.html",
        {"form": form, "qr_code_svg": img_buf.getvalue().decode("utf-8"), "b32_secret": b32_secret},
    )


@login_required
@require_POST
def remove(request, device_id):
    device_qs = twofa.models.Device.objects.active_for_user(request.user).select_subclasses()
    device = get_object_or_404(device_qs, pk=device_id)
    if not device.can_delete():
        messages.error(
            request, _('The "%(auth_name)s" authenticator cannot be removed.') % {"auth_name": device.name()}
        )
        return redirect("twofa:list")

    device.deleted_at = timezone.now()
    device.save()

    messages.success(
        request,
        _('The "%(auth_name)s" authenticator has been removed from your account.') % {"auth_name": device.name()},
    )
    if not twofa.models.Device.objects.active_for_user(request.user).exclude_backup().exists():
        request.user.twofa_enabled = False
        request.user.save()
        messages.info(
            request,
            _(
                "Since you removed the last authenticator from your account, "
                "two-factor authentication has now been disabled."
            ),
        )
    return redirect("twofa:list")


@login_required
@require_POST
def regenerate(request, device_id):
    device_qs = twofa.models.Device.objects.active_for_user(request.user).select_subclasses()
    device = get_object_or_404(device_qs, pk=device_id)
    if not device.can_regenerate():
        messages.error(
            request, _('The "%(auth_name)s" authenticator cannot be regenerated.') % {"auth_name": device.name()}
        )
        return redirect("twofa:list")

    device.regenerate()

    # TODO(lukegb): make this more general
    return redirect(reverse("twofa:paper-code", kwargs={"device_id": device.pk}))


@login_required
def list(request):
    device_qs = twofa.models.Device.objects.active_for_user(request.user).select_subclasses().order_by("last_used_at")
    can_setup = not twofa.models.TOTPDevice.objects.active_for_user(request.user).exists()
    return render(request, "twofa/list.html", {"devices": device_qs, "can_setup": can_setup})
