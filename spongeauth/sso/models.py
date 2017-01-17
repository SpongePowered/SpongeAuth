from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import User, Avatar

from .utils import send_update_ping


def _can_ping():
    return settings.DISCOURSE_SERVER and settings.DISCOURSE_API_KEY


@receiver(post_save, sender=User)
def on_user_save(sender, instance=None, **kwargs):
    if not _can_ping():
        return  # do nothing
    send_update_ping(instance)


@receiver(post_save, sender=Avatar)
def on_avatar_save(sender, instance=None, **kwargs):
    if not _can_ping():
        return  # do nothing
    if instance.user.current_avatar != instance:
        return  # no avatar update

    # This shouldn't trigger, because avatars shouldn't change once they've
    # been saved to the database, but just in case someone messes around with
    # the admin panel...
    send_update_ping(instance.user)
