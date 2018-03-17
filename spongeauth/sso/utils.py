from django.conf import settings

import requests

from accounts.models import Group
from . import discourse_sso


def _cast_bool(b):
    return str(bool(b)).lower()


def make_payload(user, nonce, request=None, group=None):
    group = group or Group
    avatar_url = user.avatar.get_absolute_url()
    if request is not None:
        avatar_url = request.build_absolute_uri(avatar_url)
    relevant_groups = group.objects.filter(internal_only=False).order_by(
        'internal_name')
    add_groups = relevant_groups.filter(user=user).values_list(
        'internal_name', flat=True)
    remove_groups = relevant_groups.exclude(user=user).values_list(
        'internal_name', flat=True)
    payload = {
        'nonce': nonce,
        'email': user.email,
        'require_activation': _cast_bool(not user.email_verified),
        'external_id': user.pk,
        'username': user.username,
        'name': user.username,
        'custom.user_field_1': user.mc_username,
        'custom.user_field_2': user.irc_nick,
        'custom.user_field_3': user.gh_username,
        'admin': user.is_admin,
        'moderator': user.is_admin or user.is_staff,
        'add_groups': ','.join(add_groups),
        'remove_groups': ','.join(remove_groups),
    }
    return payload


def send_update_ping(user, send_post=None, sso=None, group=None):
    send_post = send_post or requests.post
    sso = sso or discourse_sso.DiscourseSigner(settings.DISCOURSE_SSO_SECRET)

    out_payload, out_signature = sso.sign(make_payload(user, str(user.pk),
                                                       group=group))

    resp = send_post(
        '{}/admin/users/sync_sso'.format(settings.DISCOURSE_SERVER),
        data={
            'sso': out_payload,
            'sig': out_signature,
            'api_key': settings.DISCOURSE_API_KEY,
            'api_username': 'system'})
    resp.raise_for_status()
    return resp
