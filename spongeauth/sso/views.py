import urllib.parse

from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.conf import settings

from . import discourse_sso, utils


@login_required
def begin(request):
    raw_payload = request.GET.get("sso", "")
    raw_signature = request.GET.get("sig", "")

    for endpoint in settings.SSO_ENDPOINTS.values():
        sso = discourse_sso.DiscourseSigner(endpoint["sso_secret"])
        try:
            payload = sso.unsign(raw_payload, raw_signature)
            break
        except discourse_sso.SignatureError:
            pass
    else:
        return HttpResponseForbidden()

    if b"return_sso_url" not in payload:
        return HttpResponseForbidden()

    out_payload, out_signature = sso.sign(utils.make_payload(request.user, payload[b"nonce"]))
    redirect_to = "{}?{}".format(
        payload[b"return_sso_url"].decode("utf8"), urllib.parse.urlencode({"sso": out_payload, "sig": out_signature})
    )
    return redirect(redirect_to)
