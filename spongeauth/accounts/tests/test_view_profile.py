import io

import django.test
import django.shortcuts

from . import factories
from . import test_models
from .. import models


class TestProfile(django.test.TestCase):
    def setUp(self):
        self.user = factories.UserFactory.create()
        self.login(self.client, self.user)

    def login(self, c, user):
        assert c.login(username=user.username, password='secret')

    def path(self):
        return django.shortcuts.reverse('accounts:profile')

    def test_redirects_if_logged_out(self):
        client = django.test.Client()
        resp = client.get(self.path())
        assert resp.status_code == 302
        assert resp['Location'].startswith(django.shortcuts.reverse('accounts:login'))

    def test_get(self):
        resp = self.client.get(self.path())
        assert resp.status_code == 200
        assert set(resp.context.keys()).issuperset(
            {'profile_form', 'password_form', 'avatar_form', 'user'})

    def test_updates_profile_on_save(self):
        resp = self.client.post(self.path(), {
            'form': 'profile',
            'mc_username': 'mcloving',
            'irc_nick': 'ISeekYou',
            'gh_username': 'CodyMcCodeFace'})
        assert resp.status_code == 302
        assert resp['Location'] == self.path()
        user = models.User.objects.get(id=self.user.id)
        assert user.mc_username == 'mcloving'
        assert user.irc_nick == 'ISeekYou'
        assert user.gh_username == 'CodyMcCodeFace'

    def test_invalid_profile(self):
        resp = self.client.post(self.path(), {
            'form': 'profile',
            'mc_username': 'z' * 256,
            'irc_nick': 'ISeekYou',
            'gh_username': 'CodyMcCodeFace'})
        assert resp.status_code == 200
        user = models.User.objects.get(id=self.user.id)
        assert user.mc_username == self.user.mc_username
        assert user.irc_nick == self.user.irc_nick
        assert user.gh_username == self.user.gh_username

    def test_updates_password_on_save(self):
        assert not self.user.check_password('slartibartfast')
        resp = self.client.post(self.path(), {
            'form': 'password',
            'old_password': 'secret',
            'new_password': 'slartibartfast'})
        assert resp.status_code == 302
        assert resp['Location'] == self.path()
        user = models.User.objects.get(id=self.user.id)
        assert user.check_password('slartibartfast')

    def test_incorrect_old_password(self):
        resp = self.client.post(self.path(), {
            'form': 'password',
            'old_password': 'sekrit',
            'new_password': 'slartibartfast'})
        assert resp.status_code == 200
        user = models.User.objects.get(id=self.user.id)
        assert user.check_password('secret')

    def test_updates_avatar_on_save(self):
        assert self.user.current_avatar is None

        # set to upload
        resp = self.client.post(self.path(), {
            'form': 'avatar',
            'avatar_from': 'upload',
            'avatar_image': test_models._generate_image()})
        user = models.User.objects.get(id=self.user.id)
        assert user.current_avatar.get_absolute_url().startswith('/media/avatars/')
        assert user.current_avatar.get_absolute_url().endswith('.png')
        assert resp.status_code == 302

        # set to gravatar
        resp = self.client.post(self.path(), {
            'form': 'avatar',
            'avatar_from': 'gravatar'})
        user = models.User.objects.get(id=self.user.id)
        assert user.current_avatar.get_absolute_url().startswith('https://www.gravatar.com/')
        assert resp.status_code == 302

        # set to letter
        resp = self.client.post(self.path(), {
            'form': 'avatar',
            'avatar_from': 'letter'})
        user = models.User.objects.get(id=self.user.id)
        assert user.current_avatar is None
        assert resp.status_code == 302

    def test_select_upload_avatar_without_avatar(self):
        resp = self.client.post(self.path(), {
            'form': 'avatar',
            'avatar_from': 'upload'})
        assert resp.status_code == 200
        user = models.User.objects.get(id=self.user.id)
        assert user.current_avatar is None
