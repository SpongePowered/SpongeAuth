from django.conf import settings

import requests

from . import discourse_sso


def make_payload(user, nonce, request=None):
    avatar_url = user.avatar.get_absolute_url()
    if request is not None:
        avatar_url = request.build_absolute_uri(avatar_url)
    payload = {
        'nonce': nonce,
        'email': user.email,
        'external_id': user.pk,
        'username': user.username,
        'name': user.username,
        'custom.user_field_1': user.mc_username,
        'custom.user_field_2': user.gh_username,
        'custom.user_field_3': user.irc_nick,
    }
    return payload


def send_update_ping(user, send_post=None, sso=None):
    send_post = send_post or requests.post
    sso = sso or discourse_sso.DiscourseSigner(settings.DISCOURSE_SSO_SECRET)

    out_payload, out_signature = sso.sign(make_payload(user, str(user.pk)))

    resp = send_post(
        '{}/admin/users/sync_sso'.format(settings.DISCOURSE_SERVER),
        data={
            'sso': out_payload,
            'sig': out_signature,
            'api_key': settings.DISCOURSE_API_KEY,
            'api_username': 'system'})
    resp.raise_for_status()
    return resp
