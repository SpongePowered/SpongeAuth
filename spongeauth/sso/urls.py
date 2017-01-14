from django.conf.urls import url

import sso.views

urlpatterns = [
    url(r'^$', sso.views.begin, name='begin'),
    url(r'^sudo/$', sso.views.begin, name='sudo'),
]
