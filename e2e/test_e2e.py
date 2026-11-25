import base64
import hashlib
import hmac
import re
import secrets
import urllib.parse

import requests

from conftest import BASE_URL, SSO_SECRET, login, mail_link, new_session, post_form, url

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
FONT_MAGIC = {
    ".woff2": b"wOF2",
    ".woff": b"wOFF",
    ".ttf": b"\x00\x01\x00\x00",
    ".otf": b"OTTO",
    ".eot": None,  # no leading magic
    ".svg": None,
}


def test_healthz():
    resp = requests.get(url("/healthz"), timeout=10)
    assert (resp.status_code, resp.text) == (200, "ok")


def test_anonymous_is_sent_to_login():
    resp = requests.get(url("/"), timeout=10)
    assert urllib.parse.urlsplit(resp.url).path == "/accounts/login/"


def test_static_urls_are_hashed_and_fonts_are_intact():
    page = requests.get(url("/accounts/login/"), timeout=10).text
    stylesheets = re.findall(r'href="([^"]+\.css)"', page)
    assert stylesheets, "login page links no stylesheet"

    fonts = set()
    for href in stylesheets:
        css_url = urllib.parse.urljoin(url("/accounts/login/"), href)
        if not css_url.startswith(BASE_URL):
            continue
        assert re.search(r"\.[0-9a-f]{8,}\.css$", href), f"static URL is not hashed: {href}"
        css = requests.get(css_url, timeout=10)
        assert css.status_code == 200, f"{href}: {css.status_code}"
        for ref in re.findall(r"url\(['\"]?([^'\")]+)", css.text):
            ref = urllib.parse.urljoin(css_url, ref.split("#")[0].split("?")[0])
            if ref.endswith(tuple(FONT_MAGIC)):
                fonts.add(ref)

    assert fonts, "stylesheets reference no fonts (icon fonts missing?)"
    for font in fonts:
        resp = requests.get(font, timeout=10)
        assert resp.status_code == 200, f"{font}: {resp.status_code}"
        magic = FONT_MAGIC[font[font.rindex(".") :]]
        assert magic is None or resp.content.startswith(magic), f"{font} is corrupt"


def test_register_and_verify_email(user):
    assert user["session"].get(url("/")).status_code == 200


def test_password_login(user):
    _, resp = login(user["username"], user["password"])
    assert urllib.parse.urlsplit(resp.url).path == "/"

    _, resp = login(user["username"], "wrong-" + user["password"])
    assert urllib.parse.urlsplit(resp.url).path == "/accounts/login/"


def test_settings_and_2fa_pages_render(user):
    for path in ["/accounts/settings/", "/2fa/", "/2fa/setup/totp/"]:
        resp = user["session"].get(url(path))
        assert resp.status_code == 200 and urllib.parse.urlsplit(resp.url).path == path, path


def test_uploaded_avatar_is_served(user):
    resp = post_form(
        user["session"],
        "/accounts/settings/",
        {"form": "avatar", "avatar_from": "upload"},
        files={"avatar_image": ("avatar.png", PNG_1X1, "image/png")},
    )
    assert "Your avatar has been changed" in resp.text

    resp = requests.get(url(f"/avatar/{user['username']}"), timeout=10)
    assert resp.status_code == 200
    assert "/media/" in resp.url, f"avatar not served from media: {resp.url}"
    assert resp.content.startswith(b"\x89PNG")


def _sso_sign(payload):
    raw = base64.b64encode(urllib.parse.urlencode(payload).encode())
    return raw.decode(), hmac.new(SSO_SECRET.encode(), raw, hashlib.sha256).hexdigest()


def test_sso_round_trip(user):
    """Play the DiscourseConnect consumer (the forums, Ore) against /sso/."""
    nonce = secrets.token_hex(16)
    return_url = "https://consumer.example.com/session/sso_login"
    sso, sig = _sso_sign({"nonce": nonce, "return_sso_url": return_url})

    resp = user["session"].get(url("/sso/"), params={"sso": sso, "sig": sig}, allow_redirects=False)
    assert resp.status_code == 302 and resp.headers["Location"].startswith(return_url + "?")

    back = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(resp.headers["Location"]).query))
    want = hmac.new(SSO_SECRET.encode(), back["sso"].encode(), hashlib.sha256).hexdigest()
    assert hmac.compare_digest(back["sig"], want), "response is not signed with the shared secret"
    payload = dict(urllib.parse.parse_qsl(base64.b64decode(back["sso"]).decode()))
    assert payload["nonce"] == nonce
    assert payload["username"] == user["username"]
    assert payload["email"] == user["email"]
    assert payload["require_activation"] == "false"

    resp = user["session"].get(url("/sso/"), params={"sso": sso, "sig": "0" * 64}, allow_redirects=False)
    assert resp.status_code == 403, "a bad signature must be refused"


def test_password_reset_by_mail(user):
    s = new_session()
    resp = post_form(s, "/accounts/reset/", {"email": user["email"]})
    assert "/accounts/reset/sent/" in resp.url

    scheme, host, path = mail_link(user["email"], "/accounts/reset/")
    base = urllib.parse.urlsplit(BASE_URL)
    assert (scheme, host) == (base.scheme, base.netloc), f"mail links to {scheme}://{host}, not {BASE_URL}"

    new_password = secrets.token_urlsafe(16)
    resp = post_form(s, path, {"password": new_password})
    assert urllib.parse.urlsplit(resp.url).path == "/", f"reset failed, ended at {resp.url}"
    user["password"] = new_password

    _, resp = login(user["username"], new_password)
    assert urllib.parse.urlsplit(resp.url).path == "/"


def test_logout(user):
    s, _ = login(user["username"], user["password"])
    resp = post_form(s, "/accounts/logout/", {})
    assert "/accounts/logout/success/" in resp.url
    assert urllib.parse.urlsplit(s.get(url("/")).url).path == "/accounts/login/"
