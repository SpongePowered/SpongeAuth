from django.urls import re_path
from django.views.generic.base import RedirectView

import sso.views

app_name = "sso"

urlpatterns = [
    re_path(r"^$", sso.views.begin, name="begin"),
    re_path(r"^sudo/$", sso.views.begin, name="sudo"),
    re_path(r"^signup/$", RedirectView.as_view(pattern_name="accounts:register", permanent=False), name="signup"),
]
