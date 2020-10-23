import hashlib
import io

from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import gettext as _
from django.conf import settings as django_settings
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib import messages
import django.contrib.auth
import django.contrib.auth.views
import django.contrib.auth.tokens
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode, urlencode
from django.core.signing import Signer, BadSignature, loads, dumps

from . import models
from . import forms
from . import middleware

from oauth2client import client, crypt
from dal import autocomplete
from PIL import Image


class VerifyTokenGenerator(django.contrib.auth.tokens.PasswordResetTokenGenerator):
    key_salt = "accounts.views.verify_token_generator"

    def _make_hash_value(self, user, timestamp):
        hash_value = super()._make_hash_value(user, timestamp)
        hash_value += hashlib.sha256(user.email.encode("utf8")).hexdigest()
        return hash_value


class ForgotTokenGenerator(django.contrib.auth.tokens.PasswordResetTokenGenerator):
    key_salt = "accounts.views.forgot_token_generator"


verify_token_generator = VerifyTokenGenerator()
forgot_token_generator = ForgotTokenGenerator()


def _log_user_in(request, user, skip_twofa=False):
    # Resync groups with the TOS acceptances.
    # XXX(lukegb): this is a hack, don't do this.
    if user.pk:
        all_tos_groups = set(models.TermsOfService.objects.all().values_list("group", flat=True))
        should_tos_groups = set(user.tos_accepted.all().values_list("group", flat=True))
        current_tos_groups = set(user.groups.all().values_list("id", flat=True)) & all_tos_groups
        add_tos_groups = should_tos_groups - current_tos_groups
        remove_tos_groups = current_tos_groups - should_tos_groups
        for group in add_tos_groups:
            user.groups.add(group)
        for group in remove_tos_groups:
            user.groups.remove(group)

    if user.twofa_enabled and not skip_twofa:
        request.session["twofa_target_user"] = user.pk
        return redirect("{}?{}".format(reverse("twofa:verify"), urlencode({"next": _login_redirect_url(request)})))

    django.contrib.auth.login(request, user)
    return redirect(_login_redirect_url(request))


def _login_redirect_url(request, fallback_to=None):
    redirect_to = request.POST.get("next", request.GET.get("next", ""))
    if not redirect_to or not url_has_allowed_host_and_scheme(
        url=redirect_to, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return fallback_to or django_settings.LOGIN_REDIRECT_URL
    return redirect_to


def _obfuscate_error(msg):
    if django_settings.DEBUG:
        return msg
    return _("An error occurred logging you in. Please try again later.")


def _build_google_register_form(request, id_token, idinfo):
    initial = {
        "email": idinfo.get("email", ""),
        "username": idinfo.get("name", "").replace(" ", "_").strip()[:20],
        "google_id_token": id_token,
    }
    kwargs = {"email_editable": not idinfo.get("email_verified", False), "initial": initial}
    form = forms.RegisterGoogleForm(**kwargs)
    populate = request.POST.get("form_submitted", "no")
    if request.method == "POST" and populate == "yes":
        form = forms.RegisterGoogleForm(request.POST, **kwargs)
    return form


def _verify_google_id_token(request):
    if "google_id_token" not in request.POST:
        raise crypt.AppIdentityError("google_id_token missing.")
    token = request.POST.get("google_id_token", None)

    idinfo = client.verify_id_token(token, django_settings.GOOGLE_CLIENT_ID)
    if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
        raise crypt.AppIdentityError("Invalid issuer.")

    return token, idinfo


def _send_verify_email(request, user):
    template_kwargs = {
        "user": user,
        "link": request.build_absolute_uri(
            reverse(
                "accounts:verify-step2",
                kwargs={
                    "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
                    "token": verify_token_generator.make_token(user),
                },
            )
        ),
    }
    msg_html = render_to_string("accounts/verify/email.html", template_kwargs)
    msg_text = render_to_string("accounts/verify/email.txt", template_kwargs)
    send_mail(
        "[Sponge] Confirm your email address", msg_text, django_settings.EMAIL_FROM, [user.email], html_message=msg_html
    )


def _send_forgot_email(request, user):
    template_kwargs = {
        "user": user,
        "link": request.build_absolute_uri(
            reverse(
                "accounts:forgot-step2",
                kwargs={
                    "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
                    "token": forgot_token_generator.make_token(user),
                },
            )
        ),
        "ip": request.META["REMOTE_ADDR"],
    }
    msg_html = render_to_string("accounts/forgot/email.html", template_kwargs)
    msg_text = render_to_string("accounts/forgot/email.txt", template_kwargs)
    send_mail("[Sponge] Reset your password", msg_text, django_settings.EMAIL_FROM, [user.email], html_message=msg_html)


def _send_change_email(request, user, new_email):
    old_email = user.email
    user.email = new_email
    template_kwargs = {
        "user": user,
        "link": request.build_absolute_uri(
            reverse(
                "accounts:change-email-step2",
                kwargs={
                    "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
                    "token": verify_token_generator.make_token(user),
                    "new_email": urlsafe_base64_encode(force_bytes(new_email)),
                },
            )
        ),
    }
    user.email = old_email
    msg_html = render_to_string("accounts/change_email/email.html", template_kwargs)
    msg_text = render_to_string("accounts/change_email/email.txt", template_kwargs)
    send_mail(
        "[Sponge] Confirm your new email address",
        msg_text,
        "admin@spongepowered.org",
        [new_email],
        html_message=msg_html,
    )


def _send_email_changed_email(request, user, old_email):
    template_kwargs = {"user": user, "new_email": user.email}
    msg_html = render_to_string("accounts/change_email/confirmation_email.html", template_kwargs)
    msg_text = render_to_string("accounts/change_email/confirmation_email.txt", template_kwargs)
    send_mail(
        "[Sponge] Your email address has been changed",
        msg_text,
        "admin@spongepowered.org",
        [old_email],
        html_message=msg_html,
    )


def _make_gravatar_url(user):
    canonicalized_email = user.email.strip().lower()
    email_hash = hashlib.md5(canonicalized_email.encode("utf8")).hexdigest()
    return "https://www.gravatar.com/avatar/{}".format(email_hash)


@middleware.allow_without_verified_email
def logout(request):
    if not request.user.is_authenticated:
        return redirect("index")

    if request.method != "POST":
        return render(request, "accounts/logout.html")

    # CSRF checked automatically
    django.contrib.auth.logout(request)

    return redirect("accounts:logout-success")


def logout_success(request):
    if request.user.is_authenticated:
        return redirect("index")

    resp = render(request, "accounts/logout_success.html")
    resp["Clear-Site-Data"] = '"cache", "cookies", "storage", "executionContexts"'
    return resp


def login(request):
    if request.user.is_authenticated:
        return redirect(_login_redirect_url(request))

    # check if this is a Google login
    if request.method == "POST":
        login_type = request.POST.get("login_type", "form")
        if login_type == "google":
            return login_google(request)

    form = forms.AuthenticationForm()
    if request.method == "POST":
        form = forms.AuthenticationForm(request.POST)
        if form.is_valid() and hasattr(form, "cached_user"):
            return _log_user_in(request, form.cached_user)

    return render(request, "accounts/login.html", {"form": form, "next": _login_redirect_url(request)})


def _create_tos_acceptances_from_form(form, user):
    acceptances = []
    for tos_key, tos in form.tos_fields.items():
        if not form.cleaned_data.get(tos_key, False):
            continue
        acceptances.append(models.TermsOfServiceAcceptance(user=user, tos=tos))
    if acceptances:
        models.TermsOfServiceAcceptance.objects.bulk_create(acceptances)


def register(request):
    if request.user.is_authenticated:
        return redirect(_login_redirect_url(request))

    form = forms.RegisterForm()
    if request.method == "POST":
        form = forms.RegisterForm(request.POST)

        if form.is_valid():
            user = models.User(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                mc_username=form.cleaned_data["mc_username"],
                gh_username=form.cleaned_data["gh_username"],
                irc_nick=form.cleaned_data["irc_nick"],
            )
            user.set_password(form.cleaned_data["password"])
            user.save()
            _create_tos_acceptances_from_form(form, user)
            # _log_user_in must happen before sending the email, since the token
            # will change after the user has been logged in.
            resp = _log_user_in(request, user)
            if django_settings.REQUIRE_EMAIL_CONFIRM:
                _send_verify_email(request, user)
            return resp

    return render(request, "accounts/register.html", {"form": form, "next": _login_redirect_url(request)})


@require_POST
def login_google(request):
    try:
        token, idinfo = _verify_google_id_token(request)
    except crypt.AppIdentityError as exc:
        messages.error(request, _obfuscate_error(str(exc)))
        return redirect("accounts:login")

    try:
        ext_auth = models.ExternalAuthenticator.objects.get(
            source=models.ExternalAuthenticator.GOOGLE, external_id=idinfo["sub"]
        )

        return _log_user_in(request, ext_auth.user, skip_twofa=True)
    except models.ExternalAuthenticator.DoesNotExist:
        return register_google(request)


def register_google(request):
    token, idinfo = _verify_google_id_token(request)
    # crypt.AppIdentityError can't happen here, right now
    # since we must have made it through login_google

    form = _build_google_register_form(request, token, idinfo)
    user = None

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        # register them
        user = models.User(
            username=data.get("username", ""),
            email=data.get("email", ""),
            mc_username=data.get("mc_username", ""),
            irc_nick=data.get("irc_nick", ""),
            gh_username=data.get("gh_username", ""),
            email_verified=idinfo.get("email_verified", False),
        )
        user.set_unusable_password()
        user.save()
        _create_tos_acceptances_from_form(form, user)
        ext_auth = models.ExternalAuthenticator(
            source=models.ExternalAuthenticator.GOOGLE, external_id=idinfo["sub"], user=user
        )
        ext_auth.save()

    if user:
        resp = _log_user_in(request, user, skip_twofa=True)
        if not user.email_verified and django_settings.REQUIRE_EMAIL_CONFIRM:
            # This must happen /after/ _log_user_in.
            _send_verify_email(request, user)
        return resp

    return render(request, "accounts/register.html", {"form": form, "login_type": "google"})


@middleware.allow_without_verified_email
@login_required
def change_email(request):
    if request.method == "POST":
        form = forms.ChangeEmailForm(request.POST, user=request.user)
    else:
        form = forms.ChangeEmailForm(user=request.user)

    if request.method == "POST" and form.is_valid():
        new_email = form.cleaned_data["new_email"]
        _send_change_email(request, request.user, new_email)
        signer = Signer("accounts.views.change-email")
        email_signed = urlsafe_base64_encode(signer.sign(new_email).encode("utf8"))
        return redirect(reverse("accounts:change-email-sent") + "?e=" + email_signed)

    return render(request, "accounts/change_email/step1.html", {"form": form})


@middleware.allow_without_verified_email
@login_required
def change_email_step1done(request):
    signer = Signer("accounts.views.change-email")
    email_signed = urlsafe_base64_decode(request.GET.get("e", ""))
    try:
        email = signer.unsign(email_signed.decode("utf8"))
    except BadSignature:
        raise SuspiciousOperation("change_step1done received invalid signed email {}".format(signer))
    return render(request, "accounts/change_email/step1done.html", {"email": email})


@middleware.allow_without_verified_email
@login_required
def change_email_step2(request, uidb64, token, new_email):
    bytes_uid = urlsafe_base64_decode(uidb64)
    try:
        uid = int(bytes_uid)
    except ValueError:
        raise SuspiciousOperation("change_email_step2 received invalid base64 user ID: {}".format(bytes_uid))

    if uid != request.user.id:
        raise PermissionDenied("UID mismatch - user is {}, request was for {}".format(request.user.id, uid))

    user = get_object_or_404(models.User, pk=uid)
    old_email = user.email
    new_email = urlsafe_base64_decode(new_email).decode("utf8")
    user.email = new_email

    if not verify_token_generator.check_token(user, token):
        raise Http404("token invalid")

    if old_email == new_email:
        messages.info(request, _("Your email address has already been changed."))
    else:
        was_verified = user.email_verified
        user.email_verified = True
        user.email = new_email
        user.save()

        if was_verified:
            _send_email_changed_email(request, user, old_email)

        messages.success(request, _("Your email address has been changed successfully."))

    return redirect("index")


@middleware.allow_without_verified_email
@login_required
def verify(request):
    if request.user.email_verified:
        messages.info(request, _("Your email address has already been verified."))
        return redirect("index")

    if request.method == "POST":
        _send_verify_email(request, request.user)
        messages.info(request, _("The verification email has been sent."))
    return render(request, "accounts/verify/step1.html")


@middleware.allow_without_verified_email
@login_required
def verify_step2(request, uidb64, token):
    bytes_uid = urlsafe_base64_decode(uidb64)
    try:
        uid = int(bytes_uid)
    except ValueError:
        raise SuspiciousOperation("verify_step2 received invalid base64 user ID: {}".format(bytes_uid))
    if uid != request.user.id:
        raise PermissionDenied("UID mismatch - user is {}, request was for {}".format(request.user.id, uid))
    user = get_object_or_404(models.User, pk=uid)
    if not verify_token_generator.check_token(user, token):
        raise Http404("token invalid")

    if not user.email_verified:
        user.email_verified = True
        user.save()
        messages.success(request, _("Your email has been verified successfully. Thanks!"))
    else:
        messages.info(request, _("Your email address has already been verified."))
    return redirect("index")


def forgot(request):
    if request.user.is_authenticated:
        return redirect(_login_redirect_url(request))

    form = forms.ForgotPasswordForm()
    if request.method == "POST":
        form = forms.ForgotPasswordForm(request.POST)
        if form.is_valid():
            try:
                user = models.User.objects.get(email__iexact=form.cleaned_data["email"])
                if not user.has_usable_password():
                    form.add_error(
                        "email",
                        _(
                            "That user does not use a password to log in, "
                            "and therefore their password cannot be reset. "
                            "Did you sign up with a Google account?"
                        ),
                    )
                    user = None
            except models.User.DoesNotExist:
                form.add_error("email", _("Sorry, there is no user with that email address."))
                user = None
            if user:
                _send_forgot_email(request, user)
                signer = Signer("accounts.views.forgot-email")
                email_signed = urlsafe_base64_encode(signer.sign(user.email).encode("utf8"))
                return redirect(reverse("accounts:forgot-sent") + "?e=" + email_signed)
    return render(request, "accounts/forgot/step1.html", {"form": form})


def forgot_step1done(request):
    if request.user.is_authenticated:
        return redirect(_login_redirect_url(request))

    signer = Signer("accounts.views.forgot-email")
    email_signed = urlsafe_base64_decode(request.GET.get("e", ""))
    try:
        email = signer.unsign(email_signed.decode("utf8"))
    except BadSignature:
        raise SuspiciousOperation("forgot_step1done received invalid signed email {}".format(email_signed))
    return render(request, "accounts/forgot/step1done.html", {"email": email})


def forgot_step2(request, uidb64, token):
    if request.user.is_authenticated:
        return redirect(_login_redirect_url(request))

    bytes_uid = urlsafe_base64_decode(uidb64)
    try:
        uid = int(bytes_uid)
    except ValueError:
        raise SuspiciousOperation("forgot_step2 received invalid base64 user ID: {}".format(bytes_uid))
    user = get_object_or_404(models.User, pk=uid)
    if not forgot_token_generator.check_token(user, token):
        raise Http404("token invalid")

    form = forms.ForgotPasswordSetForm(user=user)
    if request.method == "POST":
        form = forms.ForgotPasswordSetForm(request.POST, user=user)
        if form.is_valid():
            user.set_password(form.cleaned_data["password"])
            user.save()
            messages.success(request, _("Your password has been reset, " "and you have been logged in."))
            return _log_user_in(request, user)
    return render(request, "accounts/forgot/step2.html", {"form": form, "user": user})


def _set_avatar(request, for_user):
    avatar_form = forms.SetAvatarForm(request.POST, request.FILES, user=for_user)
    if avatar_form.is_valid():
        src = avatar_form.cleaned_data["avatar_from"]
        avatar_kwargs = {"user": for_user}
        if src == forms.SetAvatarForm.UPLOAD:
            avatar_kwargs["source"] = models.Avatar.UPLOAD
            avatar_kwargs["image_file"] = avatar_form.cleaned_data["avatar_image"]
        elif src == forms.SetAvatarForm.GRAVATAR:
            avatar_kwargs["source"] = models.Avatar.URL
            avatar_kwargs["remote_url"] = _make_gravatar_url(for_user)

        if src == forms.SetAvatarForm.LETTER:
            # special case: just unset user.current_avatar
            for_user.current_avatar = None
        else:
            avatar, created = models.Avatar.objects.get_or_create(**avatar_kwargs)
            for_user.current_avatar = avatar
        for_user.save()

        return True, avatar_form
    return False, avatar_form


@login_required
def settings(request):
    user = request.user

    profile_form = forms.ProfileForm(instance=user)
    if request.method == "POST" and request.POST.get("form", "") == "profile":
        profile_form = forms.ProfileForm(request.POST, instance=user)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, _("Your profile has been saved."))
            return redirect("accounts:settings")

    password_form = forms.ChangePasswordForm(user=user)
    if request.method == "POST" and request.POST.get("form", "") == "password":
        password_form = forms.ChangePasswordForm(request.POST, user=user)
        if password_form.is_valid():
            user.set_password(password_form.cleaned_data["new_password"])
            user.save()
            messages.success(request, _("Your password has been changed."))
            return redirect("accounts:settings")

    avatar_form = forms.SetAvatarForm(user=user)
    if request.method == "POST" and request.POST.get("form", "") == "avatar":
        did_set_avatar, avatar_form = _set_avatar(request, user)
        if did_set_avatar:
            messages.success(request, _("Your avatar has been changed."))
            return redirect("accounts:settings")

    return render(
        request,
        "accounts/profile.html",
        {
            "profile_form": profile_form,
            "password_form": password_form,
            "avatar_form": avatar_form,
            "user": request.user,
        },
    )


_CHANGE_OTHER_AVATAR_SALT = "spongeauth.accounts.change_other_Avatar"


@csrf_exempt
@require_POST
def change_other_avatar_key(request, for_username):
    if "request_username" not in request.POST:
        return HttpResponse("bad request; need request_username", status=400)
    request_username = request.POST["request_username"]
    for_user = get_object_or_404(
        models.User, username=for_username, groups__internal_name__in=django_settings.ACCOUNTS_AVATAR_CHANGE_GROUPS
    )
    request_user = models.User.objects.get(username=request_username)
    data = {"target_username": for_user.username, "target_user_id": for_user.id, "request_user_id": request_user.id}
    return JsonResponse({"signed_data": dumps(data, salt=_CHANGE_OTHER_AVATAR_SALT), "raw_data": data})


@login_required
def change_other_avatar(request, for_username):
    for_user_key = request.GET.get("key", "")
    unauthorized = HttpResponse("Unauthorized", status=401)
    # Verify for_user_key against for_username first.
    try:
        for_user_data = loads(
            for_user_key, salt=_CHANGE_OTHER_AVATAR_SALT, max_age=django_settings.ACCOUNTS_AVATAR_CHANGE_MAX_AGE
        )
        all_matches = all(
            [for_user_data["target_username"] == for_username, for_user_data["request_user_id"] == request.user.id]
        )
        if not all_matches:
            raise BadSignature("data does not match")
    except BadSignature:
        return unauthorized

    # Make sure that this user is in the 'dummy' group.
    try:
        for_user = models.User.objects.get(
            username=for_username, groups__internal_name__in=django_settings.ACCOUNTS_AVATAR_CHANGE_GROUPS
        )
    except models.User.DoesNotExist:
        return unauthorized
    if for_user.id != for_user_data["target_user_id"]:
        return unauthorized

    avatar_form = forms.SetAvatarForm(user=for_user)
    if request.method == "POST":
        did_set_avatar, avatar_form = _set_avatar(request, for_user)
        if did_set_avatar:
            messages.success(request, _("The avatar has been changed."))

    return render(request, "accounts/change_other_avatar.html", {"avatar_form": avatar_form, "for_user": for_user})


def _read_filefield_to_pil(filefield):
    fh = filefield.file
    if hasattr(fh, "read") and hasattr(fh, "seek") and hasattr(fh, "tell"):
        return Image.open(fh)
    fh = io.BytesIO(filefield.read())
    return Image.open(fh)


@middleware.allow_without_verified_email
def avatar_for_user(request, username):
    user = get_object_or_404(models.User, username=username)
    avatar = user.avatar
    size = request.GET.get("size", None)
    if size:
        size_w, x, size_h = size.partition("x")
        max_dim = django_settings.ACCOUNTS_AVATAR_RESIZE_MAX_DIMENSION
        if x == "" or size_h == "":
            size_h = size_w
        try:
            size_w, size_h = int(size_w), int(size_h)
        except ValueError:
            size_w = size_h = max_dim / 2
        biggest_dim = max(size_w, size_h)
        if biggest_dim > max_dim:
            mult = max_dim / biggest_dim
            size_w = size_w * mult
            size_h = size_h * mult
        canvas_w, canvas_h = size_w, size_h

        output_format = ("PNG", "image/png")
        if "image/webp" in request.META.get("HTTP_ACCEPT", ""):
            output_format = ("WEBP", "image/webp")

        if avatar.source == models.Avatar.UPLOAD:
            pil_image = _read_filefield_to_pil(avatar.image_file)
            orig_w, orig_h = pil_image.size
            orig_ratio = orig_h / orig_w
            size_ratio = size_h / size_w
            if size_ratio < orig_ratio:
                # fit using height
                size_w = size_h / orig_ratio
            else:
                # fit using width
                size_h = size_w * orig_ratio

            pil_image = pil_image.resize((int(size_w), int(size_h)), Image.LANCZOS)
            if canvas_w != size_w or canvas_h != size_h:
                paste_x = (canvas_w - size_w) / 2
                paste_y = (canvas_h - size_h) / 2
                canvas_image = Image.new("RGBA", (int(canvas_w), int(canvas_h)), color=(0, 0, 0, 0))
                canvas_image.paste(pil_image, (int(paste_x), int(paste_y)))
                pil_image = canvas_image
            out = io.BytesIO()
            pil_image.save(out, format=output_format[0])
            return HttpResponse(out.getvalue(), output_format[1])
        elif avatar.source == models.Avatar.URL:
            # This scheme works for Gravatar *shrug*
            return redirect(user.avatar.get_absolute_url() + "?s=" + str(int(max((size_w, size_h)))))
    return redirect(user.avatar.get_absolute_url())


@middleware.allow_without_agreed_tos
def agree_tos(request):
    user = request.user
    unagreed_tos = list(user.must_agree_tos())

    if not unagreed_tos:
        return redirect(_login_redirect_url(request))

    if request.method == "POST":
        acceptances = []
        for tos in unagreed_tos:
            if request.POST.get("agree_to_tos_{}".format(tos.id), False):
                acceptances.append(models.TermsOfServiceAcceptance(user=user, tos=tos))
        if acceptances:
            models.TermsOfServiceAcceptance.objects.bulk_create(acceptances)
            unagreed_tos = list(user.must_agree_tos())
        if not unagreed_tos:
            return redirect(_login_redirect_url(request))

    has_previously_agreed_tos = models.TermsOfServiceAcceptance.objects.filter(user=user).exists()

    return render(
        request,
        "accounts/agree_tos.html",
        {"user": user, "toses": unagreed_tos, "has_previously_agreed_tos": has_previously_agreed_tos},
    )


class UserAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        users = models.User.objects.all()
        if not self.request.user.is_authenticated or not self.request.user.has_perm("accounts.view_user"):
            users = models.User.objects.none()
        if self.q:
            users = users.filter(username__istartswith=self.q)
        return users.order_by("username")
