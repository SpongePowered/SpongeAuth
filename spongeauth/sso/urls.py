from django.conf.urls import url
from django.views.generic.base import RedirectView

import sso.views

urlpatterns = [
    url(r'^$', sso.views.begin, name='begin'),
    url(r'^sudo/$', sso.views.begin, name='sudo'),
    url(r'^signup/$', RedirectView.as_view(pattern_name='accounts:register', permanent=False), name='signup'),
]
