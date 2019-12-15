import urllib.parse

from django.urls import resolve, reverse
from django.shortcuts import redirect
from django.conf import settings
import django.urls.exceptions


class RedirectIfConditionUnmet:
    REDIRECT_TO = None

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self.must_verify(request.user) and not self.may_pass(request.path):
            params = urllib.parse.urlencode({"next": request.get_full_path()})
            return redirect("{}?{}".format(reverse(self.REDIRECT_TO), params))

        response = self.get_response(request)
        return response

    @staticmethod
    def must_verify(user):
        raise NotImplementedError

    @staticmethod
    def may_pass(url):
        try:
            func = resolve(url).func
        except django.urls.exceptions.Resolver404:
            return False
        for f in ["allow_without_verified_email", "allow_without_agreed_tos"]:
            if getattr(func, f, False):
                return True
        return False


class EnforceVerifiedEmails(RedirectIfConditionUnmet):
    REDIRECT_TO = "accounts:verify"

    @staticmethod
    def must_verify(user):
        return user.is_authenticated and not user.email_verified and settings.REQUIRE_EMAIL_CONFIRM


def allow_without_verified_email(f):
    f.allow_without_verified_email = True
    return f


class EnforceToSAccepted(RedirectIfConditionUnmet):
    REDIRECT_TO = "accounts:agree-tos"

    @staticmethod
    def must_verify(user):
        if not user.is_authenticated:
            return False
        return user.must_agree_tos().exists()


def allow_without_agreed_tos(f):
    f.allow_without_agreed_tos = True
    return f
