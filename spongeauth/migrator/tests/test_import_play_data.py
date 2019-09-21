import pytest
import pytz
import faker

import accounts.models
import migrator.models
import twofa.models
from migrator.management.commands import import_play_data


@pytest.mark.django_db
def test_whole_hog():
    fake = faker.Faker()
    joined_date = fake.date_time_this_decade(tzinfo=pytz.utc)
    created_date = fake.date_time_this_decade(tzinfo=pytz.utc)
    migrator.models.User(
        id=101,
        created_at=created_date,
        join_date=joined_date,
        username="whole_hog",
        email="wholehog@example.org",
        is_email_confirmed=True,
        password="deadbeefcafe",
        mc_username="whole_hog_mc",
        irc_nick="whole_hog_irc",
        gh_username="whole_hog_gh",
        totp_secret="blah",
        is_totp_confirmed=True,
        salt="pepper",
        is_admin=True,
        failed_totp_attempts=42,
        avatar_url="https://www.example.com",
        google_id="googliness",
    ).save()

    import_play_data.Command().handle()

    assert accounts.models.User.objects.count() == 1
    user = accounts.models.User.objects.get()
    assert user.id == 101
    assert user.username == "whole_hog"
    assert user.password == "pbkdf2_sha256$64000$pepper$3q2+78r+"
    assert user.has_usable_password()
    assert user.email == "wholehog@example.org"
    assert user.email_verified
    assert user.is_active
    assert user.is_admin
    assert user.mc_username == "whole_hog_mc"
    assert user.irc_nick == "whole_hog_irc"
    assert user.gh_username == "whole_hog_gh"
    assert user.joined_at == joined_date
    assert user.deleted_at is None

    assert accounts.models.Avatar.objects.count() == 1
    avatar = accounts.models.Avatar.objects.get()
    assert avatar.user == user
    assert avatar.source == accounts.models.Avatar.URL
    assert avatar.remote_url == "https://www.example.com"
    assert user.current_avatar == avatar
    assert user.avatar == avatar

    assert accounts.models.ExternalAuthenticator.objects.count() == 1
    ext_auth = accounts.models.ExternalAuthenticator.objects.get()
    assert ext_auth.user == user
    assert ext_auth.source == accounts.models.ExternalAuthenticator.GOOGLE
    assert ext_auth.external_id == "googliness"

    assert twofa.models.TOTPDevice.objects.count() == 1
    assert twofa.models.TOTPDevice.objects.active_for_user(user).count() == 1
    totp = twofa.models.TOTPDevice.objects.get()
    assert totp.activated_at is not None
    assert totp.owner == user
    assert totp.base32_secret == "blah"


@pytest.mark.django_db
def test_minimal():
    fake = faker.Faker()
    joined_date = fake.date_time_this_decade(tzinfo=pytz.utc)
    created_date = fake.date_time_this_decade(tzinfo=pytz.utc)
    migrator.models.User(
        id=3201,
        created_at=created_date,
        join_date=joined_date,
        username="mimnal",
        email="minimal@example.org",
        is_email_confirmed=False,
        password="beeffeedcafe",
        mc_username="",
        irc_nick="",
        gh_username="",
        is_totp_confirmed=False,
        failed_totp_attempts=0,
        salt="pepper",
        is_admin=False,
        avatar_url="",
        google_id="",
    ).save()

    import_play_data.Command().handle()

    assert accounts.models.User.objects.count() == 1
    user = accounts.models.User.objects.get()
    assert user.id == 3201
    assert user.password == "pbkdf2_sha256$64000$pepper$vu/+7cr+"
    assert user.has_usable_password()
    assert user.username == "mimnal"
    assert user.email == "minimal@example.org"
    assert not user.email_verified
    assert user.is_active
    assert not user.is_admin
    assert user.joined_at == joined_date
    assert user.deleted_at is None

    assert not accounts.models.Avatar.objects.exists()
    assert not accounts.models.ExternalAuthenticator.objects.exists()
    assert not twofa.models.TOTPDevice.objects.exists()


@pytest.mark.django_db
def test_google_only():
    fake = faker.Faker()
    joined_date = fake.date_time_this_decade(tzinfo=pytz.utc)
    created_date = fake.date_time_this_decade(tzinfo=pytz.utc)
    migrator.models.User(
        id=3292,
        created_at=created_date,
        join_date=joined_date,
        username="mimnal",
        email="minimal@example.org",
        is_email_confirmed=False,
        password=None,
        mc_username="",
        irc_nick="",
        gh_username="",
        is_totp_confirmed=False,
        failed_totp_attempts=0,
        salt="pepper",
        is_admin=False,
        avatar_url="",
        google_id="googley",
    ).save()

    import_play_data.Command().handle()

    assert accounts.models.User.objects.count() == 1
    user = accounts.models.User.objects.get()
    assert user.id == 3292
    assert not user.has_usable_password()
    assert user.username == "mimnal"
    assert user.email == "minimal@example.org"
    assert not user.email_verified
    assert user.is_active
    assert not user.is_admin
    assert user.joined_at == joined_date
    assert user.deleted_at is None

    assert not accounts.models.Avatar.objects.exists()
    assert not twofa.models.TOTPDevice.objects.exists()

    assert accounts.models.ExternalAuthenticator.objects.count() == 1
    ext_auth = accounts.models.ExternalAuthenticator.objects.get()
    assert ext_auth.user == user
    assert ext_auth.source == accounts.models.ExternalAuthenticator.GOOGLE
    assert ext_auth.external_id == "googley"
