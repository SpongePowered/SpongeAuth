from django.conf import settings
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver

from accounts.models import User, Avatar

from .utils import send_update_ping


def _can_ping():
    return settings.SSO_ENDPOINTS


@receiver(post_save, sender=User)
def on_user_save(sender, instance=None, **kwargs):
    if not _can_ping():
        return  # do nothing
    send_update_ping(instance)


@receiver(m2m_changed, sender=User.groups.through)
def on_group_change(sender, instance=None, pk_set=None, action=None, reverse=None, **kwargs):
    if action not in ("post_add", "post_remove"):
        return
    if not _can_ping():
        return  # do nothing, again
    if reverse:
        instances = User.objects.filter(pk__in=pk_set)
    else:
        instances = [instance]
    for instance in instances:
        send_update_ping(instance)


@receiver(m2m_changed, sender=User.groups.through)
def on_group_clear(sender, instance=None, pk_set=None, action=None, reverse=None, **kwargs):
    if action != "pre_clear":
        return
    if not _can_ping():
        return  # do nothing, again
    if reverse:
        instances = list(instance.user_set.all())
        groups = [instance.id]
    else:
        instances = [instance]
        groups = list(instance.groups.values_list("id", flat=True))
    for instance in instances:
        send_update_ping(instance, exclude_groups=groups)


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
