"""spongeauth URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, re_path

import django_rq.urls

import accounts.urls
import api.urls
import twofa.urls
import sso.urls

from core.views import index, admin_login_redirect

from accounts.views import avatar_for_user

admin.site.site_header = admin.site.site_title = admin.site.index_title = "SpongeAuth"

urlpatterns = [
    re_path(r"^admin/login/", admin_login_redirect),
    re_path(r"^admin/", admin.site.urls),
    re_path(r"^accounts/", include(accounts.urls, "accounts")),
    re_path(r"^2fa/", include(twofa.urls, "twofa")),
    re_path(r"^avatar/(?P<username>[^/]+)/?$", avatar_for_user, name="avatar-for-user"),
    re_path(r"^sso/", include(sso.urls, "sso")),
    re_path(r"^$", index, name="index"),
    re_path(r"^api/", include(api.urls, "api")),
    re_path("django-rq/", include(django_rq.urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [re_path(r"^__djdt__/", include(debug_toolbar.urls))]
