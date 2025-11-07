from django.db import models
from django.utils import timezone


class PsnAccount(models.Model):
    username = models.CharField(max_length=100)
    npsso = models.CharField(blank=True, null=True, default=None)
    npsso_is_valid = models.BooleanField(default=False)
    available = models.BooleanField(default=True)
    ready = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return self.username
