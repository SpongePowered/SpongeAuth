import hashlib
import logging
import os.path
import re

from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.utils.translation import ugettext_lazy as _

import PIL.Image

from . import letter_avatar
import spongemime


logger = logging.getLogger(__name__)


def validate_username(username):
    errs = []
    if len(username) < 3:
        errs.append(ValidationError(
            _('Username must be at least 3 characters long.'),
            code='username_min_length'))
    if re.search(r'[^\w.-]', username):
        errs.append(ValidationError(
            _('Username must only include numbers, letters, and underscores.'),
            code='username_charset'))
    if re.search(r'\W', username[0]):
        errs.append(ValidationError(
            _('Username must begin with a number, letter or underscore.'),
            code='username_initial_charset'))
    if re.search(r'[^A-Za-z0-9]', username[-1]):
        errs.append(ValidationError(
            _('Username must end with a letter or number.'),
            code='username_ending_charset'))
    if re.search(r'[-_.]{2,}', username):
        errs.append(ValidationError(
            _('Username must not contain two special characters in a row.'),
            code='username_double_special'))
    if re.search(
            r'\.(js|json|css|htm|html|xml|jpg|jpeg|png|gif|bmp|ico|tif|tiff|woff)$',
            username):
        errs.append(ValidationError(
            _('Username must not end with a confusing file suffix.'),
            code='username_file_suffix'))
    if errs:
        raise ValidationError(errs)


def validate_discord_id(discord_id):
    if re.match(r'(.*)#(\d{4})', discord_id):
        raise ValidationError('The Discord ID must be entered in the pattern username#1234.')


class Group(models.Model):
    name = models.CharField(max_length=80, unique=True)
    internal_name = models.CharField(
        max_length=20, unique=True, blank=False, null=False,
        validators=[validate_username])

    internal_only = models.BooleanField(null=False, default=True)

    def __str__(self):
        return self.name


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
        user.is_staff = True
        user.save(using=self._db)
        return user

    def get_by_natural_key(self, username):
        return self.get(username__iexact=username)


class User(AbstractBaseUser):
    username = models.CharField(
        max_length=20, unique=True, blank=False, null=False,
        validators=[validate_username])
    email = models.EmailField(
        max_length=255, unique=True, blank=False, null=False)
    email_verified = models.BooleanField(default=False, null=False)

    is_active = models.BooleanField(default=True, null=False)
    is_staff = models.BooleanField(default=False, null=False)
    is_admin = models.BooleanField(default=False, null=False)

    full_name = models.CharField(
        max_length=255, blank=True, null=True,
        verbose_name=_('Full Name'))
    mc_username = models.CharField(
        max_length=255, blank=True, null=True,
        verbose_name=_('Minecraft Username'))
    irc_nick = models.CharField(
        max_length=255, blank=True, null=True,
        verbose_name=_('IRC Nick'))
    gh_username = models.CharField(
        max_length=255, blank=True, null=True,
        verbose_name=_('GitHub Username'))
    discord_id = models.CharField(
        max_length=255, blank=False, null=True,
        verbose_name=_('Discord ID'))

    joined_at = models.DateTimeField(
        auto_now_add=True, null=False, blank=False)
    deleted_at = models.DateTimeField(
        null=True, blank=True, default=None)

    current_avatar = models.ForeignKey(
        'Avatar', null=True, blank=True,
        related_name='+', on_delete=models.SET_NULL)

    twofa_enabled = models.BooleanField(
        default=False, null=False, verbose_name=_('2FA Enabled'))

    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        related_name='user_set',
        related_query_name='user')

    tos_accepted = models.ManyToManyField(
        'TermsOfService',
        verbose_name='terms of service',
        blank=True,
        related_name='agreed_users',
        related_query_name='agreed_users',
        through='TermsOfServiceAcceptance')

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    objects = UserManager()

    @property
    def avatar(self):
        if self.current_avatar:
            return self.current_avatar
        return letter_avatar.LetterAvatar(self.username)

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.username

    def __str__(self):
        return self.username

    def has_perm(self, perm, obj=None):
        if self.is_admin:
            return True
        elif not self.is_staff:
            return False

        if perm in ('accounts.change_user', 'accounts.change_avatar'):
            return True
        return False

    def has_module_perms(self, app_label):
        if self.is_admin:
            return True
        elif not self.is_staff:
            return False

        if app_label == 'accounts':
            return True
        return False

    def must_agree_tos(self):
        return TermsOfService.objects.filter(current_tos=True).exclude(
            agreed_users=self)

    def _test_agree_all_tos(self):
        if not self.pk:
            return
        for tos in self.must_agree_tos():
            TermsOfServiceAcceptance(
                tos=tos,
                user=self).save()


def _avatar_upload_path(instance, filename):
    instance.image_file.open('rb')
    chunk_size = 1024 * 1024 * 2
    h = hashlib.sha256()
    for chunk in instance.image_file.chunks(chunk_size):
        h.update(chunk)
    filehash = h.hexdigest()

    instance.image_file.open('rb')
    image = PIL.Image.open(instance.image_file)
    image.verify()
    mime = PIL.Image.MIME.get(image.format)
    exts = spongemime.mime2exts(mime)
    ext = exts[0] if exts else 'bin'

    bits = ('avatars',
            filehash[0:2], filehash[2:4], filehash[4:6],
            ('{}.{}'.format(filehash[6:], ext)))
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
        url = self.remote_url
        if self.source == self.UPLOAD:
            try:
                url = self.image_file.url
            except ValueError:
                # this avatar is invalid!
                logger.error('Invalid avatar', exc_info=True)
        return url or letter_avatar.LetterAvatar(self.user.username).get_absolute_url()

    def __str__(self):
        return "Avatar for {} from {}".format(self.user_id, self.get_absolute_url())


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

    def __str__(self):
        return "{} credential for user {}".format(
            self.get_source_display(),
            self.user_id)


class TermsOfService(models.Model):
    name = models.CharField(max_length=60, blank=False, null=False, unique=True)
    tos_date = models.DateField(blank=False, null=False)
    tos_url = models.URLField(blank=False, null=False, unique=True)
    current_tos = models.BooleanField(default=False, null=False)
    group = models.ForeignKey(
        Group, blank=False, null=False, on_delete=models.CASCADE)

    def __str__(self):
        return "TermsOfService: {}".format(self.name)


class TermsOfServiceAcceptance(models.Model):
    user = models.ForeignKey(
        User, null=False, blank=False, on_delete=models.CASCADE)
    tos = models.ForeignKey(
        TermsOfService, null=False, blank=False, on_delete=models.CASCADE)
    accepted_at = models.DateTimeField(
        auto_now_add=True, null=False, blank=False)

    def __str__(self):
        return "TermsOfServiceAcceptance: {} accepted {} at {}".format(
            self.user, self.tos, self.accepted_at)
