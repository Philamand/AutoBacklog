from allauth.account.signals import user_signed_up
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.http import HttpRequest
from .models import Account


@receiver(user_signed_up)
def handle_user_signed_up(request: HttpRequest, user: User, **kwargs) -> None:
    account = Account(user=user)
    account.save()
