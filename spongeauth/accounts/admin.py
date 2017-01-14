from django.contrib import admin
import django.contrib.auth.admin
import django.contrib.auth.models

from . import models

admin.site.register(models.User)
admin.site.register(models.Group)
admin.site.register(models.Avatar)
admin.site.register(models.ExternalAuthenticator)

admin.site.unregister(django.contrib.auth.models.Group)
