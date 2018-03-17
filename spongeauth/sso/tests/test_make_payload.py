import unittest.mock

import accounts.tests.factories
from .. import utils

import pytest


def test_cast_bool():
    assert utils._cast_bool(True) == 'true'
    assert utils._cast_bool(False) == 'false'
    assert utils._cast_bool(None) == 'false'


@pytest.mark.django_db
class TestMakePayload:
    def setup(self):
        self.request = unittest.mock.MagicMock()
        self.request.build_absolute_uri.return_value = 'http://www.example.com/example.jpg'

    def test_builds_payload(self):
        user = accounts.tests.factories.UserFactory.build()

        payload = utils.make_payload(user, 'nonce-nce', self.request)
        assert payload == {
            'nonce': 'nonce-nce',
            'email': user.email,
            'require_activation': 'false',
            'custom.user_field_1': user.mc_username,
            'custom.user_field_2': user.irc_nick,
            'custom.user_field_3': user.gh_username,
            'name': user.username,
            'username': user.username,
            'external_id': user.id,
            'moderator': False,
            'admin': False,
            'add_groups': '',
            'remove_groups': '',
        }

    def test_builds_payload_not_activated(self):
        user = accounts.tests.factories.UserFactory.build(
            email_verified=False)

        payload = utils.make_payload(user, 'nonce-nce', self.request)
        assert payload == {
            'nonce': 'nonce-nce',
            'email': user.email,
            'require_activation': 'true',
            'custom.user_field_1': user.mc_username,
            'custom.user_field_2': user.irc_nick,
            'custom.user_field_3': user.gh_username,
            'name': user.username,
            'username': user.username,
            'external_id': user.id,
            'moderator': False,
            'admin': False,
            'add_groups': '',
            'remove_groups': '',
        }

    def test_sends_groups(self):
        user = accounts.tests.factories.UserFactory.create()
        int_group_in = accounts.tests.factories.GroupFactory.create(
            internal_only=True)
        int_group_not_in = accounts.tests.factories.GroupFactory.create(
            internal_only=True)
        group1_in = accounts.tests.factories.GroupFactory.create(
            internal_only=False)
        group2_in = accounts.tests.factories.GroupFactory.create(
            internal_only=False)
        group1_not_in = accounts.tests.factories.GroupFactory.create(
            internal_only=False)
        group2_not_in = accounts.tests.factories.GroupFactory.create(
            internal_only=False)
        user.groups.set([int_group_in, group1_in, group2_in])
        user.save()

        del int_group_not_in  # Unused.

        payload = utils.make_payload(user, 'nonce-nce', self.request)
        assert payload == {
            'nonce': 'nonce-nce',
            'email': user.email,
            'require_activation': 'false',
            'custom.user_field_1': user.mc_username,
            'custom.user_field_2': user.irc_nick,
            'custom.user_field_3': user.gh_username,
            'name': user.username,
            'username': user.username,
            'external_id': user.id,
            'moderator': False,
            'admin': False,
            'add_groups': ','.join(sorted([group1_in.internal_name,
                                           group2_in.internal_name])),
            'remove_groups': ','.join(sorted([group1_not_in.internal_name,
                                              group2_not_in.internal_name])),
        }
