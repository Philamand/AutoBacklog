from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Account(models.Model):
    """
    Model representing a user account with additional attributes.

    Attributes:
        user (OneToOneField): A one-to-one relationship with the User model.
        npsso (CharField): A string field to store the NPSSO identifier.
        npsso_is_valid (BooleanField): A boolean field indicating if the NPSSO is valid.
        loading_data (BooleanField): A boolean field indicating if data is currently being loaded.
        last_updated (DateTimeField): A datetime field representing the last update time.

    Methods:
        __str__(): Returns the username of the user.
        is_stale(): Property method to check if the account is considered stale based on the NPSSO and last update time.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    access_token = models.BinaryField(blank=True, null=True, default=None)
    psn_token = models.BinaryField(blank=True, null=True, default=None)
    token_is_valid = models.BooleanField(default=True)
    loading_data = models.BooleanField(default=False)
    last_updated = models.DateTimeField(blank=True, null=True)
    entitlements_offset = models.IntegerField(default=0)
    last_played = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.user.username

    @property
    def is_stale(self):
        return self.psn_token and (
            not self.last_updated
            or (timezone.now() - self.last_updated).total_seconds() > 1800
        )
