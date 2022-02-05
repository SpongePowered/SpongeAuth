from django.urls import re_path

import twofa.views

app_name = "twofa"

urlpatterns = [
    re_path(r"^verify/$", twofa.views.verify, name="verify"),
    re_path(r"^verify/(?P<device_id>[0-9]+)/$", twofa.views.verify, name="verify"),
    re_path(r"^setup/totp/$", twofa.views.setup_totp, name="setup-totp"),
    re_path(r"^setup/backup/(?P<device_id>[0-9]+)/$", twofa.views.setup_backup, name="paper-code"),
    re_path(r"^remove/(?P<device_id>[0-9]+)/$", twofa.views.remove, name="remove"),
    re_path(r"^regenerate/(?P<device_id>[0-9]+)/$", twofa.views.regenerate, name="regenerate"),
    re_path(r"^$", twofa.views.list, name="list"),
]
