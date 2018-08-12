import unittest.mock

import faker
import pytest

from accounts.tests.factories import UserFactory, GroupFactory, AvatarFactory
import sso.models

TEST_SSO_ENDPOINTS = {
    'discourse': {
        'sync_sso_endpoint': (
            'http://discourse.example.com/admin/users/sync_sso'),
        'sso_secret': 'discourse-sso-secret',
        'api_key': 'discourse-api-key',
    },
}


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
    settings.SSO_ENDPOINTS = TEST_SSO_ENDPOINTS

    user = UserFactory.build()
    fake_send_update_ping.assert_not_called()

    user.save()
    fake_send_update_ping.assert_called_once_with(user)


@unittest.mock.patch('sso.models.send_update_ping')
@pytest.mark.django_db
def test_pings_on_group_save_forward(fake_send_update_ping, settings):
    user = UserFactory.create()
    group = GroupFactory.create()
    settings.SSO_ENDPOINTS = TEST_SSO_ENDPOINTS
    fake_send_update_ping.assert_not_called()

    user.groups.add(group)
    fake_send_update_ping.assert_called_once_with(user)


@unittest.mock.patch('sso.models.send_update_ping')
@pytest.mark.django_db
def test_pings_on_group_save(fake_send_update_ping, settings):
    user = UserFactory.create()
    group = GroupFactory.create()
    settings.SSO_ENDPOINTS = TEST_SSO_ENDPOINTS
    fake_send_update_ping.assert_not_called()

    group.user_set.add(user)
    fake_send_update_ping.assert_called_once_with(user)


@unittest.mock.patch('sso.models.send_update_ping')
@pytest.mark.django_db
def test_pings_on_group_clear_forward(fake_send_update_ping, settings):
    user = UserFactory.create()
    group = GroupFactory.create()
    user.groups.set([group])
    settings.SSO_ENDPOINTS = TEST_SSO_ENDPOINTS
    fake_send_update_ping.assert_not_called()

    user.groups.clear()
    assert list(fake_send_update_ping.call_args[1]['exclude_groups']) == [group.id]


@unittest.mock.patch('sso.models.send_update_ping')
@pytest.mark.django_db
def test_pings_on_group_clear(fake_send_update_ping, settings):
    user = UserFactory.create()
    group = GroupFactory.create()
    group.user_set.set([user])
    settings.SSO_ENDPOINTS = TEST_SSO_ENDPOINTS
    fake_send_update_ping.assert_not_called()

    group.user_set.clear()
    fake_send_update_ping.assert_called_once_with(user, exclude_groups=[group.id])


@unittest.mock.patch('sso.models.send_update_ping')
@pytest.mark.django_db
def test_no_pings_on_avatar_save_not_current(fake_send_update_ping, settings):
    settings.SSO_ENDPOINTS = TEST_SSO_ENDPOINTS

    user = UserFactory.create()
    fake_send_update_ping.reset_mock()

    avatar = AvatarFactory.build(user=user)
    fake_send_update_ping.assert_not_called()

    avatar.save()
    fake_send_update_ping.assert_not_called()


@unittest.mock.patch('sso.models.send_update_ping')
@pytest.mark.django_db
def test_pings_on_avatar_save_current(fake_send_update_ping, settings):
    settings.SSO_ENDPOINTS = TEST_SSO_ENDPOINTS

    user = UserFactory.create()
    avatar = AvatarFactory.create(user=user)
    user.current_avatar = avatar
    user.save()
    fake_send_update_ping.reset_mock()

    avatar.remote_url = faker.Faker().image_url()
    avatar.save()
    fake_send_update_ping.assert_called_once_with(user)
