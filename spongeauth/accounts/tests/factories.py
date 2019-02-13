import factory
import factory.django

from .. import models


class AvatarFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Avatar

    user = None
    added_at = factory.Faker('date_time_this_decade')

    source = models.Avatar.URL
    image_file = None
    remote_url = factory.Faker('image_url')

    class Params:
        uploaded = factory.Trait(
            source=models.Avatar.UPLOAD,
            image_file=factory.django.ImageField(),
            remote_url=None)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.User

    email = factory.Faker('safe_email')
    email_verified = True
    username = factory.Faker('user_name')
    password = factory.PostGenerationMethodCall('set_password', 'secret')

    full_name = factory.Faker('name')
    mc_username = factory.Faker('user_name')
    gh_username = factory.Faker('user_name')
    irc_nick = factory.Faker('user_name')
    discord_id = "user_name#1234"

    joined_at = factory.Faker('date_time_this_decade')

    tos_accepted = factory.PostGenerationMethodCall('_test_agree_all_tos')


class GroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Group

    name = factory.Faker('user_name')
    internal_name = factory.Faker('user_name')
