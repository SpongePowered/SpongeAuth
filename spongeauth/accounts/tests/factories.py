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

    mc_username = factory.Faker('user_name')
    gh_username = factory.Faker('user_name')
    irc_nick = factory.Faker('user_name')

    joined_at = factory.Faker('date_time_this_decade')
