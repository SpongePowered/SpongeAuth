import django.shortcuts

import pytest
import faker

import api.models


@pytest.fixture
def fake():
    return faker.Faker()


@pytest.mark.django_db
def test_invalid_api_key(client, fake):
    assert not api.models.APIKey.objects.exists()
    resp = client.get(django.shortcuts.reverse("api:users-list"), {"api-key": "foobar"})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_four_oh_five(client):
    api.models.APIKey.objects.create(key="foobar")

    resp = client.get(django.shortcuts.reverse("api:users-list"), {"apiKey": "foobar"})
    assert resp.status_code == 405
