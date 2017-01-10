from django.conf.urls import url

import accounts.views

RESET_TOKEN_RE = (
    r'(?P<uidb64>[0-9A-Za-z_\-]+)/'
    r'(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/')

urlpatterns = [
    url(r'^logout/$', accounts.views.logout, name='logout'),
    url(r'^logout/success/$', accounts.views.logout_success,
        name='logout-success'),

    url(r'^settings/$', accounts.views.profile, name='profile'),

    url(r'^login/$', accounts.views.login, name='login'),

    url(r'^register/$', accounts.views.register, name='register'),

    url(r'^verify/$', accounts.views.verify, name='verify'),
    url(r'^verify/' + RESET_TOKEN_RE + r'$', accounts.views.verify_step2,
        name='verify-step2'),

    url(r'^reset/$', accounts.views.forgot, name='forgot'),
    url(r'^reset/sent/$', accounts.views.forgot_step1done, name='forgot-sent'),
    url(r'^reset/' + RESET_TOKEN_RE + r'$', accounts.views.forgot_step2,
        name='forgot-step2'),
]
