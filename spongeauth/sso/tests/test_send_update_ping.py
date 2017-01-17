import unittest.mock

from accounts.tests.factories import UserFactory
from ..utils import send_update_ping


def test_send_update_ping(settings):
    fake_send_post = unittest.mock.MagicMock()
    fake_discourse_signer = unittest.mock.MagicMock()
    fake_discourse_signer.sign.return_value = (
        'payload', 'signature')

    user = UserFactory.build(
        pk=10101,
        email='foo@example.com',
        username='foo_',
        mc_username='meep',
        gh_username='meeep',
        irc_nick='XxXmeepXxX')

    settings.DISCOURSE_SERVER = 'http://discourse.example.com'
    settings.DISCOURSE_API_KEY = 'discourse-api-key'
    send_update_ping(user, send_post=fake_send_post, sso=fake_discourse_signer)

    fake_send_post.assert_called_once_with(
        'http://discourse.example.com/admin/users/sync_sso',
        data={
            'sso': 'payload',
            'sig': 'signature',
            'api_key': 'discourse-api-key',
            'api_username': 'system'})
    fake_discourse_signer.sign.assert_called_once_with({
        'nonce': '10101',
        'email': 'foo@example.com',
        'external_id': 10101,
        'username': 'foo_',
        'name': 'foo_',
        'avatar_url': user.avatar.get_absolute_url(),
        'avatar_force_update': 'true',
        'custom.user_field_1': 'meep',
        'custom.user_field_2': 'meeep',
        'custom.user_field_3': 'XxXmeepXxX'})
