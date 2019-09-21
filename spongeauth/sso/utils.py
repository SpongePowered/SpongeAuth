from django.conf import settings
from django.db.models import Q

import requests

from accounts.models import Group
from . import discourse_sso


def _cast_bool(b):
    return str(bool(b)).lower()


def make_payload(user, nonce, group=None, exclude_groups=None):
    group = group or Group
    exclude_groups = set(exclude_groups or [])
    relevant_groups = group.objects.filter(internal_only=False).order_by("internal_name")
    filter_q = Q(user=user) & ~Q(pk__in=exclude_groups)
    add_groups = relevant_groups.filter(filter_q).values_list("internal_name", flat=True)
    remove_groups = relevant_groups.exclude(filter_q).values_list("internal_name", flat=True)
    payload = {
        "nonce": nonce,
        "email": user.email,
        "require_activation": _cast_bool(not user.email_verified),
        "external_id": user.pk,
        "username": user.username,
        "name": user.full_name,
        "custom.user_field_1": user.mc_username,
        "custom.user_field_2": user.irc_nick,
        "custom.user_field_3": user.gh_username,
        "custom.user_field_4": user.discord_id,
        "admin": user.is_admin,
        "moderator": user.is_admin or user.is_staff,
        "add_groups": ",".join(add_groups),
        "remove_groups": ",".join(remove_groups),
    }
    return payload


def send_update_ping(user, send_post=None, group=None, exclude_groups=None):
    send_post = send_post or requests.post
    exclude_groups = exclude_groups or []

    payload = make_payload(user, str(user.pk), group=group, exclude_groups=exclude_groups)

    resps = []
    for endpoint_settings in settings.SSO_ENDPOINTS.values():
        if "sync_sso_endpoint" not in endpoint_settings:
            continue
        # TODO(lukegb): make this asynchronous
        sso = discourse_sso.DiscourseSigner(endpoint_settings["sso_secret"])
        out_payload, out_signature = sso.sign(payload)
        data = {
            "sso": out_payload,
            "sig": out_signature,
            "api_username": "system",
            "api_key": endpoint_settings["api_key"],
        }
        resp = send_post(endpoint_settings["sync_sso_endpoint"], data=data)
        resps.append(resp)

    # TODO(lukegb): reenable this once this is a background task.
    # for resp in resps:
    #     pass
    #     resp.raise_for_status()
