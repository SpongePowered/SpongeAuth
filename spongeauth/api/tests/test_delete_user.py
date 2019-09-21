import urllib.parse

import django.shortcuts

import pytest
import faker

import accounts.tests.factories
import api.models


@pytest.fixture
def fake():
    return faker.Faker()


def _make_path(data):
    return "{}?{}".format(django.shortcuts.reverse("api:users-list"), urllib.parse.urlencode(data))


@pytest.mark.django_db
def test_invalid_api_key(client, fake):
    assert not api.models.APIKey.objects.exists()
    resp = client.delete(_make_path({"apiKey": "foobar", "username": fake.user_name()}))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_works(client):
    api.models.APIKey.objects.create(key="foobar")

    assert not accounts.models.User.objects.exists()
    user = accounts.tests.factories.UserFactory.create()
    assert user.deleted_at is None
    assert user.is_active

    resp = client.delete(_make_path({"apiKey": "foobar", "username": user.username}))
    assert resp.status_code == 200

    # check database
    user = accounts.models.User.objects.get(id=user.id)
    assert user.deleted_at is not None
    assert not user.is_active

    # check response
    data = resp.json()
    assert data["id"] == user.id
    assert data["username"] == user.username
    assert data["email"] == user.email
    assert "avatar_url" in data


@pytest.mark.django_db
def test_not_existing(client, fake):
    api.models.APIKey.objects.create(key="foobar")

    resp = client.delete(_make_path({"apiKey": "foobar", "username": fake.user_name()}))
    assert resp.status_code == 404


@pytest.mark.django_db
def test_deleted(client, fake):
    api.models.APIKey.objects.create(key="foobar")

    user = accounts.tests.factories.UserFactory.create(deleted_at=fake.date_time_this_century(), is_active=False)

    resp = client.delete(_make_path({"apiKey": "foobar", "username": user.username}))
    assert resp.status_code == 404
