"""Black-box e2e suite: talks only HTTP to a running SpongeAuth and its Mailpit.

    E2E_BASE_URL     the instance under test     (default: the docker-compose.e2e.yml stack)
    E2E_MAILPIT_URL  Mailpit catching its mail   (default: same stack)
    E2E_SSO_SECRET   a DiscourseConnect secret the instance accepts

It seeds itself: each run registers one fresh user through the real sign-up
flow, so it needs no fixtures and is safe to re-run. Never point it at an
instance that sends real mail or syncs to real SSO consumers.
"""

import os
import re
import secrets
import time
import urllib.parse

import pytest
import requests

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:18080").rstrip("/")
MAILPIT_URL = os.environ.get("E2E_MAILPIT_URL", "http://localhost:18025").rstrip("/")
SSO_SECRET = os.environ.get("E2E_SSO_SECRET", "e2e-sso-secret")


def url(path):
    return BASE_URL + path


def new_session():
    s = requests.Session()
    s.headers["Referer"] = BASE_URL + "/"  # Django's CSRF check wants one over https
    return s


def post_form(session, path, data, **kwargs):
    """Load the form at `path`, then POST `data` to it with the page's CSRF token."""
    page = session.get(url(path))
    assert page.status_code == 200, f"GET {path}: {page.status_code}"
    token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', page.text)
    assert token, f"no CSRF token on {path}"
    return session.post(page.url, data={"csrfmiddlewaretoken": token.group(1), **data}, **kwargs)


def login(username, password):
    s = new_session()
    resp = post_form(s, "/accounts/login/", {"username": username, "password": password})
    return s, resp


def mail_link(to, path_prefix, timeout=20):
    """The first link under `path_prefix` in the newest mail to `to`, as (scheme, host, path)."""
    deadline = time.monotonic() + timeout
    while True:
        found = requests.get(f"{MAILPIT_URL}/api/v1/search", params={"query": f'to:"{to}"'}, timeout=10).json()
        for summary in found["messages"]:  # newest first
            text = requests.get(f"{MAILPIT_URL}/api/v1/message/{summary['ID']}", timeout=10).json()["Text"]
            m = re.search(r"(https?)://([^/\s]+)(" + re.escape(path_prefix) + r"\S+)", text)
            if m:
                return m.groups()
        assert time.monotonic() < deadline, f"no mail with a {path_prefix} link arrived for {to}"
        time.sleep(0.5)


@pytest.fixture(scope="session")
def user():
    """A freshly registered, email-verified user, with a logged-in session."""
    tag = secrets.token_hex(4)
    u = {"username": f"e2e_{tag}", "email": f"e2e_{tag}@example.com", "password": secrets.token_urlsafe(16)}
    s = new_session()
    # the form has one checkbox per current ToS, named by its database id
    tos = re.findall(r'name="(accept_tos_\d+)"', s.get(url("/accounts/register/")).text)
    resp = post_form(s, "/accounts/register/", {**u, **dict.fromkeys(tos, "on")})
    assert resp.status_code == 200 and "/accounts/verify/" in resp.url, f"registration failed, ended at {resp.url}"

    _, _, path = mail_link(u["email"], "/accounts/verify/")
    resp = s.get(url(path))
    assert urllib.parse.urlsplit(resp.url).path == "/", f"verification failed, ended at {resp.url}"
    u["session"] = s
    return u
