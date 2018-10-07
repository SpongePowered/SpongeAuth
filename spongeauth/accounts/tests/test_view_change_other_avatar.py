import json

import django.test
import django.shortcuts
from django.core.signing import dumps, loads

from . import factories
from . import test_models
from .. import models
from .. import views


class TestChangeOtherAvatar(django.test.TestCase):
    def setUp(self):
        self.user = factories.UserFactory.create()
        self.org_user = factories.UserFactory.create()
        self.org_user.groups.add(
            models.Group.objects.get(internal_name='dummy'))
        self.login(self.client, self.user)

    def login(self, c, user):
        assert c.login(username=user.username, password='secret')

    def path(self, for_username, key=None):
        url = django.shortcuts.reverse(
            'accounts:change-avatar', kwargs={'for_username': for_username})
        if key:
            url += '?key=' + key
        return url

    def key_for(self, for_user, req_user,
                salt=views._CHANGE_OTHER_AVATAR_SALT):
        return dumps({
            'target_username': for_user.username,
            'target_user_id': for_user.id,
            'request_user_id': req_user.id,
        },
                     salt=salt)

    def test_redirects_if_logged_out(self):
        client = django.test.Client()
        resp = client.get(self.path(self.org_user.username))
        assert resp.status_code == 302
        assert resp['Location'].startswith(
            django.shortcuts.reverse('accounts:login'))

    def test_no_key(self):
        resp = self.client.get(self.path(self.org_user.username))
        assert resp.status_code == 401

    def test_invalid_key(self):
        resp = self.client.get(
            self.path(self.org_user.username,
                      self.key_for(self.org_user, self.user, salt='asdf')))
        assert resp.status_code == 401

    def test_key_for_wrong_user(self):
        other_user = factories.UserFactory.create()
        resp = self.client.get(
            self.path(self.org_user.username,
                      self.key_for(other_user, self.user)))
        assert resp.status_code == 401

    def test_key_that_allows_wrong_user(self):
        other_user = factories.UserFactory.create()
        resp = self.client.get(
            self.path(self.org_user.username,
                      self.key_for(self.org_user, other_user)))
        assert resp.status_code == 401

    def test_key_for_non_dummy_user(self):
        other_user = factories.UserFactory.create()
        resp = self.client.get(
            self.path(other_user.username, self.key_for(other_user,
                                                        self.user)))
        assert resp.status_code == 401

    def test_get(self):
        resp = self.client.get(
            self.path(self.org_user.username,
                      self.key_for(self.org_user, self.user)))
        assert resp.status_code == 200

    def test_updates_avatar_on_save(self):
        assert self.org_user.current_avatar is None

        path = self.path(self.org_user.username,
                         self.key_for(self.org_user, self.user))

        # set to upload
        resp = self.client.post(path, {
            'avatar_from': 'upload',
            'avatar_image': test_models._generate_image()
        })
        org_user = models.User.objects.get(id=self.org_user.id)
        assert resp.status_code == 200
        assert org_user.current_avatar.get_absolute_url().startswith(
            '/media/avatars/')
        assert org_user.current_avatar.get_absolute_url().endswith('.png')

        # set to gravatar
        resp = self.client.post(path, {'avatar_from': 'gravatar'})
        org_user = models.User.objects.get(id=self.org_user.id)
        assert org_user.current_avatar.get_absolute_url().startswith(
            'https://www.gravatar.com/')
        assert resp.status_code == 200

        # set to letter
        resp = self.client.post(path, {'avatar_from': 'letter'})
        org_user = models.User.objects.get(id=self.org_user.id)
        assert org_user.current_avatar is None
        assert resp.status_code == 200


class TestChangeOtherAvatarKey(django.test.TestCase):
    def setUp(self):
        import api.models
        self.apikey = api.models.APIKey(description='', key='pew')
        self.apikey.save()
        self.user = factories.UserFactory.create()
        self.org_user = factories.UserFactory.create()
        self.org_user.groups.add(
            models.Group.objects.get(internal_name='dummy'))

    def path(self, for_username, key='pew'):
        url = django.shortcuts.reverse(
            'api:change-avatar-token', kwargs={'for_username': for_username})
        if key:
            url += '?apiKey=' + key
        return url

    def test_get_no_api_key(self):
        resp = self.client.get(self.path(self.org_user, None))
        assert resp.status_code == 403

    def test_get(self):
        resp = self.client.get(self.path(self.org_user))
        assert resp.status_code == 405

    def test_non_dummy_user(self):
        resp = self.client.post(
            self.path(self.user), {'request_username': self.user.username})
        assert resp.status_code == 404

    def test_org_user(self):
        resp = self.client.post(
            self.path(self.org_user), {'request_username': self.user.username})
        assert resp.status_code == 200
        resp_data = json.loads(resp.content)
        raw_data = resp_data['raw_data']
        assert raw_data['target_username'] == self.org_user.username
        assert raw_data['target_user_id'] == self.org_user.id
        assert raw_data['request_user_id'] == self.user.id
        dec_data = loads(
            resp_data['signed_data'], salt=views._CHANGE_OTHER_AVATAR_SALT)
        assert dec_data == raw_data

    def test_use_against_change(self):
        resp = self.client.post(
            self.path(self.org_user), {'request_username': self.user.username})
        assert resp.status_code == 200
        resp_data = json.loads(resp.content)

        url = django.shortcuts.reverse(
            'accounts:change-avatar',
            kwargs={'for_username': self.org_user.username})
        url += '?key=' + resp_data['signed_data']

        self.client.login(username=self.user.username, password='secret')

        resp = self.client.get(url)
        assert resp.status_code == 200
