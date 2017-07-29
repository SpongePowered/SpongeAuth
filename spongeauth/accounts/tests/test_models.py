import io

from django.core.files.uploadedfile import SimpleUploadedFile

import pytest

from .. import models
from .. import letter_avatar
from . import factories


class TestUser:
    def test_avatar_none_set(self):
        user = factories.UserFactory.build()
        assert user.current_avatar is None
        assert isinstance(user.avatar, letter_avatar.LetterAvatar)

    @pytest.mark.django_db
    def test_avatar_explicitly(self):
        user = factories.UserFactory.create()
        user.current_avatar = factories.AvatarFactory.create(user=user)
        user.save()

        user = models.User.objects.get(pk=user.pk)
        assert user.avatar is user.current_avatar

    def test_interface_getters(self):
        user = factories.UserFactory.build()
        assert user.get_full_name() == user.username
        assert user.get_short_name() == user.username
        assert str(user) == user.username

    def test_has_perm(self):
        user = factories.UserFactory.build()
        assert not user.has_perm('blah.create')
        assert not user.has_module_perms('blah')
        assert not user.is_staff

        staff = factories.UserFactory.build(is_admin=False, is_staff=True)
        assert not staff.has_perm('blah.create')
        assert staff.has_perm('accounts.change_user')
        assert staff.has_perm('accounts.change_avatar')
        assert staff.has_module_perms('accounts')
        assert not staff.has_module_perms('blah')

        admin = factories.UserFactory.build(is_admin=True, is_staff=True)
        assert admin.has_perm('blah.create')
        assert admin.has_module_perms('blah')
        assert admin.is_staff


@pytest.mark.django_db
class TestUserManager:
    def test_create_user(self):
        user = models.User.objects.create_user(
            username='foo', email='foo@example.com',
            password='exciting', mc_username='bar')
        assert isinstance(user, models.User)
        assert user.username == 'foo'
        assert user.email == 'foo@example.com'
        assert user.mc_username == 'bar'
        assert not user.is_admin

        assert user.password != 'exciting'
        assert user.check_password('exciting')

    def test_create_superuser(self):
        user = models.User.objects.create_superuser(
            username='foo', email='foo@example.com',
            password='exciting')
        assert isinstance(user, models.User)
        assert user.username == 'foo'
        assert user.email == 'foo@example.com'
        assert user.is_active
        assert user.is_admin

        assert user.password != 'exciting'
        assert user.check_password('exciting')

    def test_get_user_caseinsensitively(self):
        user = models.User.objects.create_user(
            username='foo', email='foo@example.com',
            password='exciting', mc_username='bar')
        assert models.User.objects.get_by_natural_key('FOO') == user
        assert models.User.objects.get_by_natural_key('Foo') == user
        assert models.User.objects.get_by_natural_key('fOo') == user
        with pytest.raises(models.User.DoesNotExist):
            models.User.objects.get_by_natural_key('bar')


def _generate_image():
    from PIL import Image
    thumb = Image.new('RGB', (100, 100), 'blue')
    thumb_io = io.BytesIO()
    thumb.save(thumb_io, format='PNG')
    thumb_io.seek(0, io.SEEK_SET)
    return SimpleUploadedFile("image.png", thumb_io.getbuffer(), content_type="image/png")


def test_avatar_upload_path():
    filename = 'foobar.jpg'

    instance = models.Avatar()
    image_buf = _generate_image()  # actually a PNG
    instance.image_file.file = image_buf
    instance.image_file.name = filename

    upload_path = models._avatar_upload_path(instance, filename)
    assert upload_path == 'avatars/3a/94/2e/13fddf9531678d6771a2d4993f6e18f5dcbbd498586444180122838de9.png'


class TestAvatar:
    @pytest.mark.django_db
    def test_get_absolute_url_upload(self):
        user = factories.UserFactory.create()
        avatar = factories.AvatarFactory.build(user=user, uploaded=True)
        assert avatar.get_absolute_url() == avatar.image_file.url

    def test_get_absolute_url_upload_invalid(self):
        user = factories.UserFactory.build(username='foobar')
        fallback = letter_avatar.LetterAvatar('foobar').get_absolute_url()
        avatar = factories.AvatarFactory.build(
            user=user, source=models.Avatar.UPLOAD, remote_url='')
        assert avatar.get_absolute_url() == fallback

    def test_get_absolute_url_remote(self):
        avatar = factories.AvatarFactory.build()
        assert avatar.get_absolute_url() == avatar.remote_url

    def test_get_absolute_url_remote_empty(self):
        user = factories.UserFactory.build(username='foobar')
        fallback = letter_avatar.LetterAvatar('foobar').get_absolute_url()
        avatar = factories.AvatarFactory.build(
            user=user, source=models.Avatar.URL, remote_url='')
        assert avatar.get_absolute_url() == fallback

    def test_str_upload(self):
        user = factories.UserFactory.build()
        avatar = factories.AvatarFactory.build(user=user, uploaded=True)
        assert str(avatar).startswith('Avatar for {} from /'.format(user.id))

    def test_str_remote(self):
        user = factories.UserFactory.build()
        avatar = factories.AvatarFactory.build(user=user)
        assert str(avatar).startswith('Avatar for {} from http'.format(user.id))


class TestGroup:
    def test_str(self):
        assert str(models.Group(name='blah')) == 'blah'


class TestExternalAuthenticator:
    def test_str(self):
        assert str(models.ExternalAuthenticator(
            user_id=21,
            source=models.ExternalAuthenticator.GOOGLE,
            external_id='blah')) == 'Google credential for user 21'
