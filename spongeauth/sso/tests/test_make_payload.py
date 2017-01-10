import unittest.mock

import accounts.tests.factories
from .. import views

import pytest


@pytest.mark.django_db
class TestMakePayload:
    def setup(self):
        self.request = unittest.mock.MagicMock()
        self.request.build_absolute_uri.return_value = 'http://www.example.com/example.jpg'

    def test_avatar_url(self):
        user = accounts.tests.factories.UserFactory.create()
        avatar = accounts.tests.factories.AvatarFactory.create(user=user)
        user.current_avatar = avatar
        user.save()

        payload = views._make_payload(user, 'nonce-nce', self.request)
        self.request.build_absolute_uri.assert_called_once_with(avatar.remote_url)
        assert payload['avatar_url'] == 'http://www.example.com/example.jpg'

    def test_builds_payload(self):
        user = accounts.tests.factories.UserFactory.build()

        payload = views._make_payload(user, 'nonce-nce', self.request)
        assert payload == {
            'nonce': 'nonce-nce',
            'email': user.email,
            'avatar_force_update': 'true',
            'avatar_url': 'http://www.example.com/example.jpg',
            'custom.user_field_1': user.mc_username,
            'custom.user_field_2': user.gh_username,
            'custom.user_field_3': user.irc_nick,
            'name': user.username,
            'username': user.username,
            'external_id': user.id
        }
