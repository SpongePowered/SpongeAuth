import io
import unittest.mock

from django.core.management import call_command, CommandError

import pytest

from accounts.tests.factories import UserFactory


@pytest.mark.django_db
def test_users_missing(settings):
    out = io.StringIO()

    user1 = UserFactory.create()
    user2 = UserFactory.create()

    with pytest.raises(CommandError) as exc:
        call_command(
            'sso_ping_discourse', 'bar', user1.username, 'baz', stdout=out)

    assert user1.username not in out.getvalue()
    assert user2.username not in str(exc.value)
    assert user2.username not in out.getvalue()

    assert str(exc.value) in (
        'User mismatch: couldn\'t find "bar", "baz"',
        'User mismatch: couldn\'t find "baz", "bar"',
    )


@pytest.mark.django_db
@unittest.mock.patch(
    'sso.management.commands.sso_ping_discourse.send_update_ping')
def test_no_args(fake_send_ping, settings):
    out = io.StringIO()

    user1 = UserFactory.create()
    user2 = UserFactory.create(is_active=False)
    user3 = UserFactory.create(email_verified=False)

    call_command('sso_ping_discourse', stdout=out)

    assert '{} OK'.format(user1.username) in out.getvalue()
    assert user2.username not in out.getvalue()
    assert user3.username not in out.getvalue()

    fake_send_ping.assert_called_once_with(user1)


@pytest.mark.django_db
@unittest.mock.patch(
    'sso.management.commands.sso_ping_discourse.send_update_ping')
def test_happy_path(fake_send_ping, settings):
    out = io.StringIO()

    user1 = UserFactory.create()
    user2 = UserFactory.create()

    def _fake_send_ping(user):
        if user == user1:
            return None
        raise ValueError('boo')

    fake_send_ping.side_effect = _fake_send_ping

    call_command(
        'sso_ping_discourse', user1.username, user2.username, stdout=out)

    assert '{} OK\n'.format(user1.username) in out.getvalue()
    assert "{} failed: ValueError('boo'".format(
        user2.username) in out.getvalue()


@pytest.mark.django_db
@unittest.mock.patch(
    'sso.management.commands.sso_ping_discourse.send_update_ping')
def test_skip_on_email_not_verified(fake_send_ping, settings):
    out = io.StringIO()

    user1 = UserFactory.create(email_verified=False)
    user2 = UserFactory.create(is_active=False)

    call_command(
        'sso_ping_discourse', user1.username, user2.username, stdout=out)

    assert '{} SKIP\n'.format(user1.username) in out.getvalue()
    assert '{} SKIP\n'.format(user2.username) in out.getvalue()
