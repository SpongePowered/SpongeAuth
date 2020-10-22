from django.conf import settings
from django.db.models import Q

import django_rq
import requests
import logging

from accounts.models import Group, User
from . import discourse_sso


def _cast_bool(b):
    return str(bool(b)).lower()


def make_payload(user, nonce, exclude_groups=None):
    exclude_groups = set(exclude_groups or [])
    relevant_groups = Group.objects.filter(internal_only=False).order_by("internal_name")
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


@django_rq.job
def send_update_ping_to_endpoint(user_id, endpoint_name, exclude_groups):
    endpoint_settings = settings.SSO_ENDPOINTS.get(endpoint_name)
    if not endpoint_settings:
        return
    if "sync_sso_endpoint" not in endpoint_settings:
        return
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return
    payload = make_payload(user, str(user.pk), exclude_groups=exclude_groups)
    sso = discourse_sso.DiscourseSigner(endpoint_settings["sso_secret"])
    out_payload, out_signature = sso.sign(payload)
    data = {"sso": out_payload, "sig": out_signature, "api_username": "system", "api_key": endpoint_settings["api_key"]}
    resp = requests.post(endpoint_settings["sync_sso_endpoint"], data=data)
    if resp.status_code >= 400:
        logging.warning("SSO Sync error: " + resp.text)
    resp.raise_for_status()


def send_update_ping(user, exclude_groups=None):
    exclude_groups = exclude_groups or []

    for endpoint_name, endpoint_settings in settings.SSO_ENDPOINTS.items():
        if "sync_sso_endpoint" not in endpoint_settings:
            continue
        send_update_ping_to_endpoint.delay(user.pk, endpoint_name, exclude_groups)
