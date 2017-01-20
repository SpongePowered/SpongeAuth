from django.contrib import admin
import django.contrib.auth.admin
import django.contrib.auth.models

from . import models


class UserAdmin(admin.ModelAdmin):
    raw_id_fields = ("current_avatar",)


class AvatarAdmin(admin.ModelAdmin):
    raw_id_fields = ("user",)


class ExternalAuthenticatorAdmin(admin.ModelAdmin):
    raw_id_fields = ("user",)


admin.site.register(models.User, UserAdmin)
admin.site.register(models.Group)
admin.site.register(models.Avatar, AvatarAdmin)
admin.site.register(models.ExternalAuthenticator, ExternalAuthenticatorAdmin)

admin.site.unregister(django.contrib.auth.models.Group)
