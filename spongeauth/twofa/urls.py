from django.conf.urls import url

import twofa.views

urlpatterns = [
    url(r'^verify/$', twofa.views.verify, name='verify'),
    url(r'^verify/(?P<device_id>[0-9]+)/$', twofa.views.verify, name='verify'),
    url(r'^setup/totp/$', twofa.views.setup_totp, name='setup-totp'),
    url(r'^setup/backup/(?P<device_id>[0-9]+)/$', twofa.views.setup_backup, name='paper-code'),
    url(r'^remove/(?P<device_id>[0-9]+)/$', twofa.views.remove, name='remove'),
    url(r'^regenerate/(?P<device_id>[0-9]+)/$', twofa.views.regenerate, name='regenerate'),
    url(r'^$', twofa.views.list, name='list'),
]
