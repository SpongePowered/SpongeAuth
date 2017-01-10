from django.urls import resolve
from django.shortcuts import redirect


class EnforceVerifiedEmails:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self.must_verify(request.user) and not self.may_pass(request.path):
            return redirect('accounts:verify')

        response = self.get_response(request)
        return response

    @staticmethod
    def must_verify(user):
        return user.is_authenticated() and not user.email_verified

    @staticmethod
    def may_pass(url):
        return getattr(
            resolve(url).func, 'allow_without_verified_email', False)


def allow_without_verified_email(f):
    f.allow_without_verified_email = True
    return f
