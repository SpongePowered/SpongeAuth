from django.db import models


class APIKey(models.Model):
    key = models.CharField(max_length=52, null=False, blank=False)
    description = models.CharField(max_length=255, null=False, blank=True, default='')
