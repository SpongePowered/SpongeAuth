import django.test
import django.shortcuts
import django.http
import django.core.signing
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

import unittest.mock

from . import factories
from .. import forms
from .. import models


class TestForgot(django.test.TestCase):
    def setUp(self):
        self.user = factories.UserFactory.create()
        self.client = django.test.Client()

    def login(self, c, user):
        assert c.login(username=user.username, password="secret")

    def path(self):
        return django.shortcuts.reverse("accounts:forgot")

    def test_redirects_if_logged_in(self):
        self.login(self.client, self.user)
        resp = self.client.get(self.path())
        assert resp.status_code == 302
        assert resp["Location"] == "/"

    @unittest.mock.patch("accounts.views._send_forgot_email")
    def test_renders_page_on_get(self, mock_send_forgot_email):
        resp = self.client.get(self.path())
        assert resp.status_code == 200
        self.assertTemplateUsed(resp, "accounts/forgot/step1.html")
        mock_send_forgot_email.assert_not_called()

    @unittest.mock.patch("accounts.views._send_forgot_email")
    def test_invalid_form(self, mock_send_forgot_email):
        resp = self.client.post(self.path(), {"email": ""})
        assert resp.status_code == 200
        mock_send_forgot_email.assert_not_called()

    @unittest.mock.patch("accounts.views._send_forgot_email")
    def test_sends_email_on_post(self, mock_send_forgot_email):
        resp = self.client.post(self.path(), {"email": self.user.email}, follow=True)
        assert resp.status_code == 200
        assert self.user.email.encode("utf8") in resp.content
        assert len(resp.redirect_chain) == 1

        mock_send_forgot_email.assert_called_once()
        args, kwargs = mock_send_forgot_email.call_args
        assert len(args) == 2
        assert args[1] == self.user

    @unittest.mock.patch("accounts.views._send_forgot_email")
    def test_unusable_password(self, mock_send_forgot_email):
        self.user.set_unusable_password()
        self.user.save()
        resp = self.client.post(self.path(), {"email": self.user.email})
        assert resp.status_code == 200
        mock_send_forgot_email.assert_not_called()

    @unittest.mock.patch("accounts.views._send_forgot_email")
    def test_no_such_email(self, mock_send_forgot_email):
        resp = self.client.post(self.path(), {"email": self.user.email + ".ru"})
        assert resp.status_code == 200
        mock_send_forgot_email.assert_not_called()


class TestForgotStep1Done(django.test.TestCase):
    def setUp(self):
        self.user = factories.UserFactory.create()
        self.client = django.test.Client()

    def login(self, c, user):
        assert c.login(username=user.username, password="secret")

    def path(self, e=None):
        path = django.shortcuts.reverse("accounts:forgot-sent")
        if e:
            path += "?e=" + urlsafe_base64_encode(e.encode("utf8"))
        return path

    @unittest.mock.patch("accounts.views.Signer")
    def test_redirects_if_logged_in(self, mock_signer):
        self.login(self.client, self.user)
        resp = self.client.get(self.path("asdf"))
        assert resp.status_code == 302
        assert resp["Location"] == "/"
        mock_signer.assert_not_called()

    @unittest.mock.patch("accounts.views.Signer")
    def test_valid_signature(self, mock_signer):
        mock_signer.return_value.unsign.return_value = "foo@example.org"
        resp = self.client.get(self.path())
        mock_signer.assert_called_once()
        assert resp.status_code == 200
        assert b"foo@example.org" in resp.content

    @unittest.mock.patch("accounts.views.Signer")
    def test_invalid_signature(self, mock_signer):
        mock_signer.return_value.unsign.side_effect = django.core.signing.BadSignature("failed")
        resp = self.client.get(self.path())
        mock_signer.assert_called_once()
        assert resp.status_code == 400


class TestForgotStep2(django.test.TestCase):
    def setUp(self):
        self.user = factories.UserFactory.create()
        self.client = django.test.Client()

        patcher = unittest.mock.patch("accounts.views.forgot_token_generator")
        self.mock_token_generator = patcher.start()
        self.mock_token_generator.check_token.return_value = True
        self.addCleanup(patcher.stop)

    def login(self, c, user):
        assert c.login(username=user.username, password="secret")

    def path(self, user, token, uidb64=None):
        return django.shortcuts.reverse(
            "accounts:forgot-step2",
            kwargs={"uidb64": uidb64 or urlsafe_base64_encode(force_bytes(user.id)), "token": token},
        )

    def test_redirects_if_logged_in(self):
        self.login(self.client, self.user)
        resp = self.client.get(self.path(self.user, "deadbeef-cafe"))
        assert resp.status_code == 302
        assert resp["Location"] == "/"

    def test_bad_user_id(self):
        resp = self.client.get(self.path(None, "deadbeef-cafe", uidb64="foo"))
        assert resp.status_code == 400

    def test_bad_token(self):
        self.mock_token_generator.check_token.return_value = False
        resp = self.client.get(self.path(self.user, "deadbeef-cafe"))
        assert resp.status_code == 404

    @unittest.mock.patch("accounts.views._log_user_in")
    def test_renders_form_on_get(self, mock_log_user_in):
        resp = self.client.get(self.path(self.user, "deadbeef-cafe"))
        assert resp.status_code == 200
        assert isinstance(resp.context["form"], forms.ForgotPasswordSetForm)
        mock_log_user_in.assert_not_called()

    @unittest.mock.patch("accounts.views._log_user_in")
    def test_sets_password_on_post(self, mock_log_user_in):
        mock_log_user_in.return_value = django.http.HttpResponse("yay")
        assert not self.user.check_password("slartibartfast")
        resp = self.client.post(self.path(self.user, "deadbeef-cafe"), {"password": "slartibartfast"})
        assert resp is mock_log_user_in.return_value

        user = models.User.objects.get(id=self.user.id)
        assert user.check_password("slartibartfast")

        mock_log_user_in.assert_called_once()
        args, kwargs = mock_log_user_in.call_args
        assert len(args) == 2
        assert args[1] == user

    @unittest.mock.patch("accounts.views._log_user_in")
    def test_invalid_password(self, mock_log_user_in):
        assert not self.user.check_password(self.user.username)
        resp = self.client.post(self.path(self.user, "deadbeef-cafe"), {"password": self.user.username})
        assert resp.status_code == 200
        assert isinstance(resp.context["form"], forms.ForgotPasswordSetForm)
        mock_log_user_in.assert_not_called()
