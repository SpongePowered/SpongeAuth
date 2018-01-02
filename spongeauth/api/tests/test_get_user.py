import django.shortcuts

import pytest
import faker

import accounts.models
import accounts.tests.factories
import api.models


@pytest.fixture
def fake():
    return faker.Faker()


@pytest.mark.django_db
def test_invalid_api_key(client, fake):
    assert not api.models.APIKey.objects.exists()
    resp = client.get(django.shortcuts.reverse(
        'api:users-detail', kwargs={'username': fake.user_name()}), {
            'apiKey': 'foobar'})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_existing_user(client, fake):
    api.models.APIKey.objects.create(key='foobar')

    user = accounts.tests.factories.UserFactory.create()
    resp = client.get(django.shortcuts.reverse(
        'api:users-detail', kwargs={'username': user.username}), {
            'apiKey': 'foobar'})
    assert resp.status_code == 200

    data = resp.json()
    assert data['id'] == user.id
    assert data['username'] == user.username
    assert data['email'] == user.email
    assert 'avatar_url' in data


@pytest.mark.django_db
def test_deleted_user(client, fake):
    api.models.APIKey.objects.create(key='foobar')

    user = accounts.tests.factories.UserFactory.create(
        is_active=False,
        deleted_at=fake.date_time_this_century())
    resp = client.get(django.shortcuts.reverse(
        'api:users-detail', kwargs={'username': user.username}), {
            'apiKey': 'foobar'})
    assert resp.status_code == 404


@pytest.mark.django_db
def test_nonexistent_user(client, fake):
    api.models.APIKey.objects.create(key='foobar')

    resp = client.get(django.shortcuts.reverse(
        'api:users-detail', kwargs={'username': fake.user_name()}), {
            'apiKey': 'foobar'})
    assert resp.status_code == 404


@pytest.mark.django_db
def test_existing_user_in_group(client, fake):
    api.models.APIKey.objects.create(key='foobar')

    user = accounts.tests.factories.UserFactory.create()
    group = accounts.tests.factories.GroupFactory.create()
    user.groups.set([group])
    user.save()

    resp = client.get(django.shortcuts.reverse(
        'api:users-detail', kwargs={'username': user.username}), {
            'apiKey': 'foobar'})
    assert resp.status_code == 200

    data = resp.json()
    assert 'groups' in data
    assert len(data['groups']) == 1
    assert data['groups'][0] == {
        'id': group.id,
        'name': group.name,
    }
