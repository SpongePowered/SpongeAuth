from django.contrib import admin
from django import forms
import django.contrib.auth.admin
import django.contrib.auth.forms
import django.contrib.auth.models
from django.utils import timezone

from . import models


class AdminUserChangeForm(forms.ModelForm):
    password = django.contrib.auth.forms.ReadOnlyPasswordHashField(
        help_text="Raw passwords are not stored, so there is no way to see "
                  "this user's password, but you can change the password "
                  "using <a href=\"../password/\">this form</a>."
    )

    def clean_password(self):
        return self.initial['password']

    class Meta:
        model = models.User
        fields = (
            'username', 'password', 'email', 'email_verified', 'is_active', 'current_avatar', 'twofa_enabled',
            'is_admin', 'is_staff',
            'mc_username', 'irc_nick', 'gh_username')


class UserAdmin(django.contrib.auth.admin.UserAdmin):
    raw_id_fields = ("current_avatar",)
    fieldsets = (
        (None, {
            'fields': (
                'username', 'password', 'email', 'email_verified',
                'is_active', 'is_admin', 'is_staff', 'current_avatar', 'twofa_enabled'),
        }),
        ('Profile fields', {
            'classes': ('collapse',),
            'fields': ('mc_username', 'irc_nick', 'gh_username'),
        }),
    )
    filter_horizontal = ()
    list_display = ('username', 'email', 'is_active', 'twofa_enabled')
    list_filter = ('is_admin', 'twofa_enabled')
    search_fields = ['username', 'email']
    form = AdminUserChangeForm

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_admin:
            return self.readonly_fields

        if obj and not obj.is_admin:
            return self.readonly_fields + ('is_admin', 'is_staff')

        return list(set(
            [field.name for field in self.opts.local_fields] +
            [field.name for field in self.opts.local_many_to_many]
        ))

    def delete_model(self, request, obj):
        obj.deleted_at = timezone.now()
        obj.is_active = False
        obj.save()


class AvatarAdmin(admin.ModelAdmin):
    raw_id_fields = ("user",)


class ExternalAuthenticatorAdmin(admin.ModelAdmin):
    raw_id_fields = ("user",)


admin.site.register(models.User, UserAdmin)
admin.site.register(models.Group)
admin.site.register(models.Avatar, AvatarAdmin)
admin.site.register(models.ExternalAuthenticator, ExternalAuthenticatorAdmin)

admin.site.unregister(django.contrib.auth.models.Group)
