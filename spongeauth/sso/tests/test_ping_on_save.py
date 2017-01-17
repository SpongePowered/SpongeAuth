import unittest.mock

import faker
import pytest

from accounts.tests.factories import UserFactory, AvatarFactory
import sso.models


@unittest.mock.patch('sso.models.send_update_ping')
def test_no_ping_by_default_test(fake_send_update_ping):
    assert not sso.models._can_ping()

    sso.models.on_user_save(None)
    fake_send_update_ping.assert_not_called()

    sso.models.on_avatar_save(None)
    fake_send_update_ping.assert_not_called()


@unittest.mock.patch('sso.models.send_update_ping')
@pytest.mark.django_db
def test_pings_on_user_save(fake_send_update_ping, settings):
    settings.DISCOURSE_SERVER = 'http://discourse.example.com'
    settings.DISCOURSE_API_KEY = 'discourse-api-key'

    user = UserFactory.build()
    fake_send_update_ping.assert_not_called()

    user.save()
    fake_send_update_ping.assert_called_once_with(user)


@unittest.mock.patch('sso.models.send_update_ping')
@pytest.mark.django_db
def test_no_pings_on_avatar_save_not_current(fake_send_update_ping, settings):
    settings.DISCOURSE_SERVER = 'http://discourse.example.com'
    settings.DISCOURSE_API_KEY = 'discourse-api-key'

    user = UserFactory.create()
    fake_send_update_ping.reset_mock()

    avatar = AvatarFactory.build(user=user)
    fake_send_update_ping.assert_not_called()

    avatar.save()
    fake_send_update_ping.assert_not_called()


@unittest.mock.patch('sso.models.send_update_ping')
@pytest.mark.django_db
def test_pings_on_avatar_save_current(fake_send_update_ping, settings):
    settings.DISCOURSE_SERVER = 'http://discourse.example.com'
    settings.DISCOURSE_API_KEY = 'discourse-api-key'

    user = UserFactory.create()
    avatar = AvatarFactory.create(user=user)
    user.current_avatar = avatar
    user.save()
    fake_send_update_ping.reset_mock()

    avatar.remote_url = faker.Faker().image_url()
    avatar.save()
    fake_send_update_ping.assert_called_once_with(user)
