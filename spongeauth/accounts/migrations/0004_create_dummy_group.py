# -*- coding: utf-8 -*-
# Creates "Dummy" group, used to flag dummy accounts created by API.
from __future__ import unicode_literals

from django.db import migrations


def forwards_func(apps, schema_editor):
    Group = apps.get_model("accounts", "Group")
    db_alias = schema_editor.connection.alias
    Group.objects.using(db_alias).bulk_create([Group(name="Dummy")])


def reverse_func(apps, schema_editor):
    Group = apps.get_model("accounts", "Group")
    db_alias = schema_editor.connection.alias
    Group.objects.using(db_alias).filter(name="Dummy").delete()


class Migration(migrations.Migration):

    dependencies = [("accounts", "0003_create_group_model")]

    operations = [migrations.RunPython(forwards_func, reverse_func)]
