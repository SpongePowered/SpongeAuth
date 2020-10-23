from django.conf.urls import url

import accounts.views

app_name = "accounts"

RESET_TOKEN_RE = r"(?P<uidb64>[0-9A-Za-z_\-]+)/" r"(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,32})/"

urlpatterns = [
    url(r"^logout/$", accounts.views.logout, name="logout"),
    url(r"^logout/success/$", accounts.views.logout_success, name="logout-success"),
    url(r"^settings/$", accounts.views.settings, name="settings"),
    url(r"^login/$", accounts.views.login, name="login"),
    url(r"^register/$", accounts.views.register, name="register"),
    url(r"^verify/$", accounts.views.verify, name="verify"),
    url(r"^verify/" + RESET_TOKEN_RE + r"$", accounts.views.verify_step2, name="verify-step2"),
    url(r"^change-email/$", accounts.views.change_email, name="change-email"),
    url(r"^change-email/sent/$", accounts.views.change_email_step1done, name="change-email-sent"),
    url(
        r"^change-email/" + RESET_TOKEN_RE + r"(?P<new_email>[0-9A-Za-z_\-]+)/$",
        accounts.views.change_email_step2,
        name="change-email-step2",
    ),
    url(r"^reset/$", accounts.views.forgot, name="forgot"),
    url(r"^reset/sent/$", accounts.views.forgot_step1done, name="forgot-sent"),
    url(r"^reset/" + RESET_TOKEN_RE + r"$", accounts.views.forgot_step2, name="forgot-step2"),
    url(r"^agree-tos/$", accounts.views.agree_tos, name="agree-tos"),
    url(r"^user/(?P<for_username>[^/]+)/change-avatar/$", accounts.views.change_other_avatar, name="change-avatar"),
    url(r"^__internal/autocomplete/users/$", accounts.views.UserAutocomplete.as_view(), name="users-autocomplete"),
]
