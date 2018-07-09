import unittest.mock

from accounts.tests.factories import UserFactory
from .. import discourse_sso
from ..utils import send_update_ping

TEST_SSO_ENDPOINTS = {
    'discourse': {
        'sync_sso_endpoint': (
            'http://discourse.example.com/admin/users/sync_sso'),
        'sso_secret': 'discourse-sso-secret',
        'api_key': 'discourse-api-key',
    },
}


def test_send_update_ping(settings):
    with unittest.mock.patch.object(discourse_sso, 'DiscourseSigner') as \
            fake_discourse_signer_cls:
        fake_send_post = unittest.mock.MagicMock()
        fake_discourse_signer = fake_discourse_signer_cls.return_value
        fake_discourse_signer.sign.return_value = (
            'payload', 'signature')
        fake_group = unittest.mock.MagicMock()
        filt_group = (
                fake_group.objects.filter.return_value.order_by.return_value)
        filt_group.filter.return_value.values_list.return_value = [
            'aardvark', 'banana', 'carrot']
        filt_group.exclude.return_value.values_list.return_value = [
            'gingerbread', 'horseradish', 'indigo']

        user = UserFactory.build(
            pk=10101,
            email='foo@example.com',
            username='foo_',
            mc_username='meep',
            gh_username='meeep',
            irc_nick='XxXmeepXxX')

        settings.SSO_ENDPOINTS = TEST_SSO_ENDPOINTS
        send_update_ping(user, send_post=fake_send_post,
                         group=fake_group)

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
            'require_activation': 'false',
            'external_id': 10101,
            'username': 'foo_',
            'name': 'foo_',
            'custom.user_field_1': 'meep',
            'custom.user_field_2': 'XxXmeepXxX',
            'custom.user_field_3': 'meeep',
            'moderator': False,
            'admin': False,
            'add_groups': 'aardvark,banana,carrot',
            'remove_groups': 'gingerbread,horseradish,indigo',
        })
