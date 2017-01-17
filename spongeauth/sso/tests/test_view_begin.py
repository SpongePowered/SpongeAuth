import urllib.parse
import unittest.mock

import django.test
import django.shortcuts

import pytest

import accounts.tests.factories
from .. import discourse_sso


@pytest.mark.django_db
@django.test.override_settings(DISCOURSE_SSO_SECRET='slartibartfast')
class TestBegin(django.test.TestCase):
    def setUp(self):
        self.user = accounts.tests.factories.UserFactory.create()
        self.signer = discourse_sso.DiscourseSigner('slartibartfast')

        self.client = django.test.Client()
        self.login(self.client, self.user)

    def login(self, c, user):
        assert c.login(username=user.username, password='secret')

    def path(self, params=None):
        path = django.shortcuts.reverse('sso:begin')
        if params:
            path += '?' + urllib.parse.urlencode(params)
        return path

    def test_requires_login(self):
        client = django.test.Client()
        resp = client.get(self.path())
        assert resp.status_code == 302

    def test_no_sso_payload(self):
        resp = self.client.get(self.path())
        assert resp.status_code == 403

    def test_invalid_sso_payload(self):
        resp = self.client.get(self.path({'sso': 'blah', 'sig': 'nope'}))
        assert resp.status_code == 403

    @unittest.mock.patch('sso.utils.make_payload')
    def test_valid(self, mock_make_payload):
        mock_make_payload.return_value = {b'yooo': b'hooo'}

        sso, sig = self.signer.sign({'nonce': '123456', 'return_sso_url': '/hi/i/am/sso'})
        resp = self.client.get(self.path({'sso': sso, 'sig': sig}))
        assert resp.status_code == 302
        assert resp['Location'].startswith('/hi/i/am/sso?')
        qs = resp['Location'][len('/hi/i/am/sso?'):]
        params = urllib.parse.parse_qs(qs)
        assert set(params.keys()) == {'sso', 'sig'}
        assert all([len(x) == 1 for x in params.values()])
        try:
            vals = self.signer.unsign(params['sso'][0], params['sig'][0])
            assert vals == mock_make_payload.return_value
        except discourse_sso.SignatureError as exc:
            self.fail(exc)

    def test_feedback(self):
        sso, sig = self.signer.sign({'nonce': '123456', 'return_sso_url': '/hi/i/am/sso'})
        resp = self.client.get(self.path({'sso': sso, 'sig': sig}))
        assert resp.status_code == 302
        assert resp['Location'].startswith('/hi/i/am/sso?')
        qs = resp['Location'][len('/hi/i/am/sso?'):]
        params = urllib.parse.parse_qs(qs)
        assert set(params.keys()) == {'sso', 'sig'}
        assert all([len(x) == 1 for x in params.values()])

        reresp = self.client.get(self.path({'sso': params['sso'][0], 'sig': params['sig'][0]}))
        assert reresp.status_code == 403
