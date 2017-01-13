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
    resp = client.post(django.shortcuts.reverse('api:users-list'), {
        'api-key': 'foobar',
        'username': fake.user_name(),
        'email': fake.safe_email(),
        'verified': 'true',
        'dummy': 'false'})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_works(client, fake):
    api.models.APIKey.objects.create(key='foobar')
    assert not accounts.models.User.objects.exists()
    username, email = fake.user_name(), fake.safe_email()
    resp = client.post(django.shortcuts.reverse('api:users-list'), {
        'api-key': 'foobar',
        'username': username,
        'password': 'barfoo',
        'email': email,
        'verified': 'true',
        'dummy': 'false'})
    assert resp.status_code == 201
    assert resp['Location'] == django.shortcuts.reverse('api:users-detail', kwargs={'username': username})

    # check database
    assert accounts.models.User.objects.exists()
    user = accounts.models.User.objects.get()
    assert user.username == username
    assert user.email == email
    assert user.check_password('barfoo')
    assert user.email_verified

    data = resp.json()
    assert data['id'] == user.id
    assert data['username'] == user.username
    assert data['email'] == user.email
    assert 'avatar_url' in data


@pytest.mark.django_db
def test_sets_verified_correctly(client, fake):
    api.models.APIKey.objects.create(key='barshu')
    assert not accounts.models.User.objects.exists()
    username, email = fake.user_name(), fake.safe_email()
    resp = client.post(django.shortcuts.reverse('api:users-list'), {
        'api-key': 'barshu',
        'username': username,
        'password': 'oofbar',
        'email': email,
        'verified': 'false',
        'dummy': 'false'})
    assert resp.status_code == 201
    assert resp['Location'] == django.shortcuts.reverse('api:users-detail', kwargs={'username': username})

    # check database
    assert accounts.models.User.objects.exists()
    user = accounts.models.User.objects.get()
    assert not user.email_verified


@pytest.mark.django_db
def test_create_already_exists(client, fake):
    api.models.APIKey.objects.create(key='barshu')
    user = accounts.tests.factories.UserFactory.create()

    resp = client.post(django.shortcuts.reverse('api:users-list'), {
        'api-key': 'barshu',
        'username': user.username,
        'password': 'oofbar',
        'email': fake.email(),
        'verified': 'false',
        'dummy': 'false'})
    assert resp.status_code == 422

    data = resp.json()
    assert 'error' in data
