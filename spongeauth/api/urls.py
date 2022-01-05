from django.urls import re_path

import api.views

app_name = "api"

urlpatterns = [
    re_path(r"^users$", api.views.list_users, name="users-list"),
    re_path(r"^users/(?P<username>[^/]+)$", api.views.user_detail, name="users-detail"),
    re_path(
        r"^users/(?P<for_username>[^/]+)/change-avatar-token/$",
        api.views.change_other_avatar_key,
        name="change-avatar-token",
    ),
]
