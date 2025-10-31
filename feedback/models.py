from django.db import models
from django.conf import settings


TYPES = [("fdk", "General Feedback"), ("bug", "Bug Report"), ("fea", "Feature Request")]


class Feedback(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    type = models.CharField(max_length=3, choices=TYPES, default="fdk")
    message = models.TextField()
    processed = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.message[:20] + "..."
