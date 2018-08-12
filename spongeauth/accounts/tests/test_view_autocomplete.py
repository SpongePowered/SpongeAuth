import django.test
import django.shortcuts

from . import factories
from . import test_models
from .. import models

import json


class TestViewAutocomplete(django.test.TestCase):
    def setUp(self):
        self.user = factories.UserFactory.create(
            is_staff=True, is_admin=True)
        self.client = django.test.Client()
        assert self.client.login(username=self.user.username, password='secret')

    def path(self):
        return django.shortcuts.reverse('accounts:users-autocomplete')

    def test_get_no_permission(self):
        self.user.is_staff = False
        self.user.is_admin = False
        self.user.save()
        resp = self.client.get(self.path())
        assert resp.status_code == 200
        resp_dict = json.loads(resp.content)
        assert resp_dict['results'] == []

    def test_get_without_query(self):
        resp = self.client.get(self.path())
        assert resp.status_code == 200
        resp_dict = json.loads(resp.content)
        assert resp_dict['results'] == [
            {
                "id": str(self.user.id),
                "text": self.user.username,
                "selected_text": self.user.username,
            }
        ]

    def test_get_with_query_match(self):
        resp = self.client.get(self.path() + '?q=' + self.user.username[:2])
        assert resp.status_code == 200
        resp_dict = json.loads(resp.content)
        assert resp_dict['results'] == [
            {
                "id": str(self.user.id),
                "text": self.user.username,
                "selected_text": self.user.username,
            }
        ]

    def test_get_with_query_no_match(self):
        resp = self.client.get(self.path() + '?q=!')
        assert resp.status_code == 200
        resp_dict = json.loads(resp.content)
        assert resp_dict['results'] == []
