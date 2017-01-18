import hashlib

from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.utils.translation import ugettext as _
from django.conf import settings as django_settings
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib import messages
import django.contrib.auth
import django.contrib.auth.views
import django.contrib.auth.tokens
from django.contrib.auth.decorators import login_required
from django.utils.http import is_safe_url
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode, urlencode
from django.core.signing import Signer, BadSignature

from . import models
from . import forms
from . import middleware

from oauth2client import client, crypt


class VerifyTokenGenerator(django.contrib.auth.tokens.PasswordResetTokenGenerator):
    key_salt = 'accounts.views.verify_token_generator'

    def _make_hash_value(self, user, timestamp):
        hash_value = super()._make_hash_value(user, timestamp)
        hash_value += hashlib.sha256(user.email.encode('utf8')).hexdigest()
        return hash_value


class ForgotTokenGenerator(django.contrib.auth.tokens.PasswordResetTokenGenerator):
    key_salt = 'accounts.views.forgot_token_generator'

verify_token_generator = VerifyTokenGenerator()
forgot_token_generator = ForgotTokenGenerator()


def _log_user_in(request, user, skip_twofa=False):
    if user.twofa_enabled and not skip_twofa:
        request.session['twofa_target_user'] = user.pk
        return redirect('{}?{}'.format(
            reverse('twofa:verify'),
            urlencode({'next': _login_redirect_url(request)})))

    django.contrib.auth.login(request, user)
    return redirect(_login_redirect_url(request))


def _login_redirect_url(request, fallback_to=None):
    redirect_to = request.POST.get('next', request.GET.get('next', ''))
    if not redirect_to or not is_safe_url(url=redirect_to, host=request.get_host()):
        return fallback_to or django_settings.LOGIN_REDIRECT_URL
    return redirect_to


def _obfuscate_error(msg):
    if django_settings.DEBUG:
        return msg
    return _("An error occurred logging you in. Please try again later.")


def _build_google_register_form(request, id_token, idinfo):
    initial = {
        'email': idinfo.get('email', ''),
        'username': idinfo.get('name', '').replace(' ', '_').strip()[:20],
        'google_id_token': id_token,
    }
    kwargs = {
        'email_editable': not idinfo.get('email_verified', False),
        'initial': initial,
    }
    form = forms.RegisterGoogleForm(**kwargs)
    populate = request.POST.get('form_submitted', 'no')
    if request.method == 'POST' and populate == 'yes':
        form = forms.RegisterGoogleForm(request.POST, **kwargs)
    return form


def _verify_google_id_token(request):
    if 'google_id_token' not in request.POST:
        raise crypt.AppIdentityError("google_id_token missing.")
    token = request.POST.get('google_id_token', None)

    idinfo = client.verify_id_token(token, django_settings.GOOGLE_CLIENT_ID)
    if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
        raise crypt.AppIdentityError("Invalid issuer.")

    return token, idinfo


def _send_verify_email(request, user):
    template_kwargs = {
        'user': user,
        'link': request.build_absolute_uri(reverse('accounts:verify-step2', kwargs={
            'uidb64': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': verify_token_generator.make_token(user),
        })),
    }
    msg_html = render_to_string('accounts/verify/email.html', template_kwargs)
    msg_text = render_to_string('accounts/verify/email.txt', template_kwargs)
    send_mail(
        '[Sponge] Confirm your email address',
        msg_text,
        'admin@spongepowered.org',
        [user.email],
        html_message=msg_html,
    )


def _send_forgot_email(request, user):
    template_kwargs = {
        'user': user,
        'link': request.build_absolute_uri(reverse('accounts:forgot-step2', kwargs={
            'uidb64': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': forgot_token_generator.make_token(user),
        })),
        'ip': request.META['REMOTE_ADDR'],
    }
    msg_html = render_to_string('accounts/forgot/email.html', template_kwargs)
    msg_text = render_to_string('accounts/forgot/email.txt', template_kwargs)
    send_mail(
        '[Sponge] Reset your password',
        msg_text,
        'admin@spongepowered.org',
        [user.email],
        html_message=msg_html,
    )


def _make_gravatar_url(user):
    canonicalized_email = user.email.strip().lower()
    email_hash = hashlib.md5(canonicalized_email.encode('utf8')).hexdigest()
    return 'https://www.gravatar.com/avatar/{}'.format(email_hash)


@middleware.allow_without_verified_email
def logout(request):
    if not request.user.is_authenticated():
        return redirect('index')

    if request.method != 'POST':
        return render(request, 'accounts/logout.html')

    # CSRF checked automatically
    django.contrib.auth.logout(request)

    return redirect('accounts:logout-success')


def logout_success(request):
    if request.user.is_authenticated():
        return redirect('index')
    return render(request, 'accounts/logout_success.html')


def login(request):
    if request.user.is_authenticated():
        return redirect(_login_redirect_url(request))

    # check if this is a Google login
    if request.method == 'POST':
        login_type = request.POST.get('login_type', 'form')
        if login_type == 'google':
            return login_google(request)

    form = forms.AuthenticationForm()
    if request.method == 'POST':
        form = forms.AuthenticationForm(request.POST)
        if form.is_valid() and hasattr(form, 'cached_user'):
            return _log_user_in(request, form.cached_user)

    return render(request, 'accounts/login.html', {'form': form})


def register(request):
    if request.user.is_authenticated():
        return redirect(_login_redirect_url(request))

    form = forms.RegisterForm()
    if request.method == 'POST':
        form = forms.RegisterForm(request.POST)

        if form.is_valid():
            user = models.User(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                mc_username=form.cleaned_data['mc_username'],
                gh_username=form.cleaned_data['gh_username'],
                irc_nick=form.cleaned_data['irc_nick'])
            user.set_password(form.cleaned_data['password'])
            user.save()
            # _log_user_in must happen before sending the email, since the token
            # will change after the user has been logged in.
            resp = _log_user_in(request, user)
            if django_settings.REQUIRE_EMAIL_CONFIRM:
                _send_verify_email(request, user)
            return resp

    return render(request, 'accounts/register.html', {'form': form})


@require_POST
def login_google(request):
    try:
        token, idinfo = _verify_google_id_token(request)
    except crypt.AppIdentityError as exc:
        messages.error(request, _obfuscate_error(str(exc)))
        return redirect('accounts:login')

    try:
        ext_auth = models.ExternalAuthenticator.objects.get(
            source=models.ExternalAuthenticator.GOOGLE,
            external_id=idinfo['sub'])

        return _log_user_in(request, ext_auth.user, skip_twofa=True)
    except models.ExternalAuthenticator.DoesNotExist:
        return register_google(request)


def register_google(request):
    token, idinfo = _verify_google_id_token(request)
    # crypt.AppIdentityError can't happen here, right now
    # since we must have made it through login_google

    form = _build_google_register_form(request, token, idinfo)
    user = None

    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        # register them
        user = models.User(
            username=data.get('username', ''),
            email=data.get('email', ''),
            mc_username=data.get('mc_username', ''),
            irc_nick=data.get('irc_nick', ''),
            gh_username=data.get('gh_username', ''),
            email_verified=idinfo.get('email_verified', False))
        user.set_unusable_password()
        user.save()
        ext_auth = models.ExternalAuthenticator(
            source=models.ExternalAuthenticator.GOOGLE,
            external_id=idinfo['sub'],
            user=user)
        ext_auth.save()

    if user:
        resp = _log_user_in(request, user, skip_twofa=True)
        if not user.email_verified and django_settings.REQUIRE_EMAIL_CONFIRM:
            # This must happen /after/ _log_user_in.
            _send_verify_email(request, user)
        return resp

    return render(request, 'accounts/register.html', {'form': form, 'login_type': 'google'})


@middleware.allow_without_verified_email
@login_required
def verify(request):
    if request.user.email_verified:
        messages.info(request, _('Your email address has already been verified.'))
        return redirect('index')

    if request.method == 'POST':
        _send_verify_email(request, request.user)
        messages.info(request, _('The verification email has been sent.'))
    return render(request, 'accounts/verify/step1.html')


@middleware.allow_without_verified_email
@login_required
def verify_step2(request, uidb64, token):
    bytes_uid = urlsafe_base64_decode(uidb64)
    try:
        uid = int(bytes_uid)
    except ValueError:
        raise SuspiciousOperation('verify_step2 received invalid base64 user ID: {}'.format(
            bytes_uid))
    if uid != request.user.id:
        raise PermissionDenied('UID mismatch - user is {}, request was for {}'.format(
            request.user.id, uid))
    user = get_object_or_404(models.User, pk=uid)
    if not verify_token_generator.check_token(user, token):
        raise Http404('token invalid')

    if not user.email_verified:
        user.email_verified = True
        user.save()
        messages.success(request, _('Your email has been verified successfully. Thanks!'))
    else:
        messages.info(request, _('Your email address has already been verified.'))
    return redirect('index')


def forgot(request):
    if request.user.is_authenticated():
        return redirect(_login_redirect_url(request))

    form = forms.ForgotPasswordForm()
    if request.method == 'POST':
        form = forms.ForgotPasswordForm(request.POST)
        if form.is_valid():
            try:
                user = models.User.objects.get(email=form.cleaned_data['email'])
                if not user.has_usable_password():
                    form.add_error(
                        'email',
                        _('That user does not use a password to log in, and therefore their password cannot be reset. '
                          'Did you sign up with a Google account?'))
                    user = None
            except models.User.DoesNotExist:
                form.add_error('email', _('Sorry, there is no user with that email address.'))
                user = None
            if user:
                _send_forgot_email(request, user)
                signer = Signer('accounts.views.forgot-email')
                email_signed = urlsafe_base64_encode(signer.sign(user.email.encode('utf8')).encode('utf8'))
                return redirect(reverse('accounts:forgot-sent') + '?e=' + email_signed.decode('utf8'))
    return render(request, 'accounts/forgot/step1.html', {'form': form})


def forgot_step1done(request):
    if request.user.is_authenticated():
        return redirect(_login_redirect_url(request))

    signer = Signer('accounts.views.forgot-email')
    email_signed = urlsafe_base64_decode(request.GET.get('e', ''))
    try:
        email = signer.unsign(email_signed)
    except BadSignature:
        raise SuspiciousOperation('forgot_step1done received invalid signed email {}'.format(signer))
    return render(request, 'accounts/forgot/step1done.html', {'email': email})


def forgot_step2(request, uidb64, token):
    if request.user.is_authenticated():
        return redirect(_login_redirect_url(request))

    bytes_uid = urlsafe_base64_decode(uidb64)
    try:
        uid = int(bytes_uid)
    except ValueError:
        raise SuspiciousOperation('forgot_step2 received invalid base64 user ID: {}'.format(
            bytes_uid))
    user = get_object_or_404(models.User, pk=uid)
    if not forgot_token_generator.check_token(user, token):
        raise Http404('token invalid')

    form = forms.ForgotPasswordSetForm(user=user)
    if request.method == 'POST':
        form = forms.ForgotPasswordSetForm(request.POST, user=user)
        if form.is_valid():
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(
                request, _('Your password has been reset, '
                           'and you have been logged in.'))
            return _log_user_in(request, user)
    return render(
        request, 'accounts/forgot/step2.html', {'form': form, 'user': user})


@login_required
def settings(request):
    user = request.user

    profile_form = forms.ProfileForm(instance=user)
    if request.method == 'POST' and request.POST.get('form', '') == 'profile':
        profile_form = forms.ProfileForm(request.POST, instance=user)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, _('Your profile has been saved.'))
            return redirect('accounts:settings')

    password_form = forms.ChangePasswordForm(user=user)
    if request.method == 'POST' and request.POST.get('form', '') == 'password':
        password_form = forms.ChangePasswordForm(request.POST, user=user)
        if password_form.is_valid():
            user.set_password(password_form.cleaned_data['new_password'])
            user.save()
            messages.success(request, _('Your password has been changed.'))
            return redirect('accounts:settings')

    avatar_form = forms.SetAvatarForm(user=user)
    if request.method == 'POST' and request.POST.get('form', '') == 'avatar':
        avatar_form = (
            forms.SetAvatarForm(request.POST, request.FILES, user=user))
        if avatar_form.is_valid():
            src = avatar_form.cleaned_data['avatar_from']
            avatar_kwargs = {
                'user': user,
            }
            if src == forms.SetAvatarForm.UPLOAD:
                avatar_kwargs['source'] = models.Avatar.UPLOAD
                avatar_kwargs['image_file'] = (
                    avatar_form.cleaned_data['avatar_image'])
            elif src == forms.SetAvatarForm.GRAVATAR:
                avatar_kwargs['source'] = models.Avatar.URL
                avatar_kwargs['remote_url'] = _make_gravatar_url(user)

            if src == forms.SetAvatarForm.LETTER:
                # special case: just unset user.current_avatar
                user.current_avatar = None
            else:
                avatar, created = (
                    models.Avatar.objects.get_or_create(**avatar_kwargs))
                user.current_avatar = avatar
            user.save()

            messages.success(request, _('Your avatar has been changed.'))
            return redirect('accounts:settings')

    return render(request, 'accounts/profile.html', {
        'profile_form': profile_form,
        'password_form': password_form,
        'avatar_form': avatar_form,
        'user': request.user})


def avatar_for_user(request, username):
    user = get_object_or_404(models.User, username=username)
    return redirect(user.avatar.get_absolute_url())
