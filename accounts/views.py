import json
import os
from typing import Any
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from cryptography.fernet import Fernet
from .models import Account
from games.tasks import load_games


class RegisterView(TemplateView):
    """
    RegisterView is a view for user registration.
    Handles POST requests to create a new user account and associated Account model.
    Validates the UserCreationForm data, saves the new user, and creates an Account instance linked to the user.
    Redirects to the login page upon successful registration.
    Renders the registration template with the form if the form data is invalid.
    """

    template_name = "registration/register.html"

    def post(self, request: HttpRequest) -> HttpResponse:
        """
        Handles POST requests for user registration.
        Validates the UserCreationForm data, saves the new user, and creates an Account instance linked to the user.
        Redirects to the login page upon successful registration.
        Renders the registration template with the form if the form data is invalid.
        """
        form = UserCreationForm(request.POST)
        email = request.POST.get("email")
        email_error = None
        try:
            validate_email(email)
            if form.is_valid():
                form.save()
                user = User.objects.get(username=form.cleaned_data["username"])
                user.email = email
                user.save()
                account = Account(user=user)
                account.save()
                return redirect("login")
        except ValidationError:
            email_error = "Please enter a valid email."
        return render(
            request, self.template_name, {"form": form, "email_error": email_error}
        )


class SettingsView(LoginRequiredMixin, TemplateView):
    """
    SettingsView is a view for user account settings.
    Allows users to update their account information via POST requests.
    """

    template_name = "accounts/settings.html"

    def post(self, request: HttpRequest) -> HttpResponse:
        """
        Handles POST requests to update the user's account settings.
        Updates the user's Account model with the provided data.
        Redirects to the 'games' page upon successful update.
        """
        account = Account.objects.filter(user=request.user)
        f = Fernet(
            os.getenv("FERNET_KEY").encode() # type: ignore
        )
        n = self.request.POST.get("npsso")
        if n:
            npsso = f.encrypt(n.encode())
            account.update(psn_token=npsso, loading_data=True)
            load_games.send(request.user.id)  # type: ignore
        return redirect("games")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Retrieves and prepares context data for the settings view.

        This method extends the base context by adding the user's npsso token,
        the validity status of the npsso token, and the current theme from the session.

        Returns:
        - dict[str, Any]: A dictionary containing the context data.
        """
        context = super().get_context_data(**kwargs)
        f = Fernet(
            os.getenv("FERNET_KEY").encode() # type: ignore
        )
        npsso = self.request.user.account.psn_token
        if npsso:
            npsso = f.decrypt(npsso).decode()
        context["npsso"] = npsso
        context["token_is_valid"] = self.request.user.account.token_is_valid
        context["theme"] = self.request.session.get("theme")

        return context


@login_required
def toggle_theme(request: HttpRequest) -> HttpResponse:
    """
    Toggles the user's theme preference.

    This view processes a POST request to switch the user's theme between 'light' and 'dark'.
    It updates the theme in the session if the provided theme is valid ('light' or 'dark').

    Parameters:
    - request (HttpRequest): The HTTP request object containing the theme data in the body.

    Returns:
    - HttpResponse: A response with a status code of 200 upon successful theme update.
    """
    theme = json.loads(request.body)["theme"]
    if theme == "light" or theme == "dark":
        request.session["theme"] = theme
        request.session.save()
    return HttpResponse(status=200)
