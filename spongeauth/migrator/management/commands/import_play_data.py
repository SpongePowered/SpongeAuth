import base64
import binascii

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

import migrator.models
import accounts.models
import twofa.models


class Command(BaseCommand):
    help = "Imports SpongeAuth data from Play implementation."

    def handle(self, *args, **options):
        now = timezone.now()
        with transaction.atomic():
            for muser in migrator.models.User.objects.all():
                auser = accounts.models.User(
                    id=muser.id,
                    username=muser.username,
                    email=muser.email,
                    email_verified=muser.is_email_confirmed,
                    is_active=True,
                    is_admin=muser.is_admin,
                    mc_username=muser.mc_username,
                    irc_nick=muser.irc_nick,
                    gh_username=muser.gh_username,
                    joined_at=muser.join_date,
                    deleted_at=None,
                )
                if muser.password:
                    auser.password = "pbkdf2_sha256${iterations}${salt}${password_b64}".format(
                        iterations=64000,
                        salt=muser.salt,
                        password_b64=base64.b64encode(binascii.unhexlify(muser.password)).decode("ascii"),
                    )
                else:
                    auser.set_unusable_password()
                auser.save()
                if muser.is_totp_confirmed:
                    twofa.models.TOTPDevice(
                        owner=auser, last_t=0, drift=0, activated_at=now, base32_secret=muser.totp_secret
                    ).save()
                    auser.totp_enabled = True
                if muser.avatar_url:
                    avatar = accounts.models.Avatar(
                        user=auser, remote_url=muser.avatar_url, source=accounts.models.Avatar.URL
                    )
                    avatar.save()
                    auser.current_avatar = avatar
                if muser.google_id:
                    accounts.models.ExternalAuthenticator(
                        user=auser, source=accounts.models.ExternalAuthenticator.GOOGLE, external_id=muser.google_id
                    ).save()
                auser.save()

                accounts.models.User.objects.filter(id=muser.id).update(joined_at=muser.join_date)
