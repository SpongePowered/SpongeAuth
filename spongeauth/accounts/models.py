from django.utils.translation import ugettext_lazy as _

import hashlib
import os.path

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

from . import letter_avatar


class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **kwargs):
        user = self.model(
            username=username,
            email=self.normalize_email(email),
            **kwargs)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password):
        user = self.create_user(username, email, password)
        user.is_active = True
        user.is_admin = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    username = models.CharField(
        max_length=20, unique=True, blank=False, null=False)
    email = models.EmailField(
        max_length=255, unique=True, blank=False, null=False)
    email_verified = models.BooleanField(default=False, null=False)

    is_active = models.BooleanField(default=True, null=False)
    is_admin = models.BooleanField(default=False, null=False)

    mc_username = models.CharField(
        max_length=255, blank=True, null=True,
        verbose_name=_('Minecraft Username'))
    irc_nick = models.CharField(
        max_length=255, blank=True, null=True,
        verbose_name=_('IRC Nick'))
    gh_username = models.CharField(
        max_length=255, blank=True, null=True,
        verbose_name=_('GitHub Username'))

    joined_at = models.DateTimeField(
        auto_now_add=True, null=False, blank=False)
    deleted_at = models.DateTimeField(
        null=True, blank=True, default=None)

    current_avatar = models.ForeignKey(
        'Avatar', null=True, blank=True,
        related_name='+', on_delete=models.SET_NULL)

    twofa_enabled = models.BooleanField(
        default=False, null=False, verbose_name=_('2FA Enabled'))

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    objects = UserManager()

    @property
    def avatar(self):
        if self.current_avatar:
            return self.current_avatar
        return letter_avatar.LetterAvatar(self.username)

    def get_full_name(self):
        return self.username

    def get_short_name(self):
        return self.username

    def __str__(self):
        return self.username

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return self.is_admin

    @property
    def is_staff(self):
        return self.is_admin


def _avatar_upload_path(instance, filename):
    instance.image_file.open('rb')
    chunk_size = 1024 * 1024 * 2
    h = hashlib.sha256()
    for chunk in instance.image_file.chunks(chunk_size):
        h.update(chunk)
    _, ext = os.path.splitext(filename)
    filehash = h.hexdigest()
    bits = ('avatars',
            filehash[0:2], filehash[2:4], filehash[4:6],
            ('{}{}'.format(filehash[6:], ext)))
    path = os.path.join(*bits)
    return path


class Avatar(models.Model):
    UPLOAD = 'upload'
    URL = 'url'
    AVATAR_CHOICES = (
        (UPLOAD, _("Uploaded avatar")),
        (URL, _("Avatar at URL")),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True, blank=False, null=False)

    image_file = models.ImageField(
        null=True, blank=True, upload_to=_avatar_upload_path)
    remote_url = models.URLField(null=True, blank=True)

    source = models.CharField(
        max_length=10, choices=AVATAR_CHOICES, default=UPLOAD,
        blank=False, null=False)

    def get_absolute_url(self):
        if self.source == self.UPLOAD:
            return self.image_file.url
        return self.remote_url


class ExternalAuthenticator(models.Model):
    GOOGLE = 'google'
    SOURCE_CHOICES = (
        (GOOGLE, _("Google")),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    source = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, default=GOOGLE,
        blank=False, null=False)

    external_id = models.CharField(max_length=255, blank=False, null=False)
