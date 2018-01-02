from django.conf.urls import url

import api.views

app_name = 'api'

urlpatterns = [
    url(r'^users$', api.views.list_users, name='users-list'),
    url(r'^users/(?P<username>[a-zA-Z0-9_\-]+)$', api.views.user_detail, name='users-detail'),
]
