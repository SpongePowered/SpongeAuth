from django.core.management.base import BaseCommand, CommandError

from sso.utils import send_update_ping
from accounts.models import User


class Command(BaseCommand):
    help = 'Update Discourse with user information'

    def add_arguments(self, parser):
        parser.add_argument('username', nargs='*', type=str)

    def send_update(self, user):
        return send_update_ping(user)

    def handle(self, *args, **options):
        if options['username']:
            users = list(User.objects.filter(username__in=options['username']))
            usernames = {user.username for user in users}
            if usernames != set(options['username']):
                raise CommandError('User mismatch: couldn\'t find "{}"'.format(
                    '", "'.join(set(options['username']) - usernames)))
        else:
            users = list(User.objects.filter(is_active=True, email_verified=True))

        for user in users:
            self.stdout.write(user.username, ending=' ')

            if not user.is_active or not user.email_verified:
                self.stdout.write(self.style.WARNING('SKIP'))
                continue

            try:
                self.send_update(user)
                self.stdout.write(self.style.SUCCESS('OK'))
            except Exception as ex:
                self.stdout.write(self.style.ERROR('failed: {}'.format(repr(ex))))
