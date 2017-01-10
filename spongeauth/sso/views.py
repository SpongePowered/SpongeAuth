import urllib.parse

from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.conf import settings

from . import discourse_sso

sso = discourse_sso.DiscourseSigner(settings.DISCOURSE_SSO_SECRET)


def _make_payload(user, nonce, request=None):
    avatar_url = user.avatar.get_absolute_url()
    if request is not None:
        avatar_url = request.build_absolute_uri(avatar_url)
    payload = {
        'nonce': nonce,
        'email': user.email,
        'external_id': user.pk + 9999999,
        'username': user.username,
        'name': user.username,
        'avatar_url': avatar_url,
        'avatar_force_update': 'true',
        'custom.user_field_1': user.mc_username,
        'custom.user_field_2': user.gh_username,
        'custom.user_field_3': user.irc_nick,
    }
    return payload


@login_required
def begin(request):
    raw_payload = request.GET.get('sso', '')
    raw_signature = request.GET.get('sig', '')
    try:
        payload = sso.unsign(raw_payload, raw_signature)
    except discourse_sso.SignatureError:
        return HttpResponseForbidden()

    payload = {k: v[0] for k, v in payload.items()}

    out_payload, out_signature = sso.sign(_make_payload(request.user, payload[b'nonce']))
    redirect_to = '{}?{}'.format(
        payload[b'return_sso_url'].decode('utf8'),
        urllib.parse.urlencode({
            'sso': out_payload,
            'sig': out_signature}))
    return redirect(redirect_to)
