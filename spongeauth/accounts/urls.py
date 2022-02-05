from django.urls import re_path

import accounts.views

app_name = "accounts"

RESET_TOKEN_RE = r"(?P<uidb64>[0-9A-Za-z_\-]+)/" r"(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,32})/"

urlpatterns = [
    re_path(r"^logout/$", accounts.views.logout, name="logout"),
    re_path(r"^logout/success/$", accounts.views.logout_success, name="logout-success"),
    re_path(r"^settings/$", accounts.views.settings, name="settings"),
    re_path(r"^login/$", accounts.views.login, name="login"),
    re_path(r"^register/$", accounts.views.register, name="register"),
    re_path(r"^verify/$", accounts.views.verify, name="verify"),
    re_path(r"^verify/" + RESET_TOKEN_RE + r"$", accounts.views.verify_step2, name="verify-step2"),
    re_path(r"^change-email/$", accounts.views.change_email, name="change-email"),
    re_path(r"^change-email/sent/$", accounts.views.change_email_step1done, name="change-email-sent"),
    re_path(
        r"^change-email/" + RESET_TOKEN_RE + r"(?P<new_email>[0-9A-Za-z_\-]+)/$",
        accounts.views.change_email_step2,
        name="change-email-step2",
    ),
    re_path(r"^reset/$", accounts.views.forgot, name="forgot"),
    re_path(r"^reset/sent/$", accounts.views.forgot_step1done, name="forgot-sent"),
    re_path(r"^reset/" + RESET_TOKEN_RE + r"$", accounts.views.forgot_step2, name="forgot-step2"),
    re_path(r"^agree-tos/$", accounts.views.agree_tos, name="agree-tos"),
    re_path(r"^user/(?P<for_username>[^/]+)/change-avatar/$", accounts.views.change_other_avatar, name="change-avatar"),
    re_path(r"^__internal/autocomplete/users/$", accounts.views.UserAutocomplete.as_view(), name="users-autocomplete"),
]
