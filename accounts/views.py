import json
import os
from typing import Any
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from cryptography.fernet import Fernet
from .models import Account, EntitlementsUpload, EntitlementsDownload
from games.tasks import (
    get_account_id,
    load_games,
    download_entitlements,
    load_entitlements,
)
from games.models import Game


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
        f = Fernet(
            os.getenv("FERNET_KEY").encode()  # type: ignore
        )
        user = User.objects.prefetch_related("account").get(pk=self.request.user.id)
        npsso = self.request.POST.get("npsso")
        playstation_username = self.request.POST.get("playstationUsername")
        if npsso:
            if user.account.account_id:
                encrypted_npsso = f.encrypt(npsso.encode())
                entitlement_download = EntitlementsDownload(
                    user=user, npsso=encrypted_npsso
                )
                entitlement_download.save()
                user.account.loading_data = True
                user.account.save()
                if user.account.is_stale:
                    download_entitlements.send(entitlement_download.pk)
                else:
                    load_games.send(
                        user_id=user.pk, download_id=entitlement_download.pk
                    )
                return redirect("games")
            else:
                messages.error(
                    self.request,
                    "Please provide your PlayStation username before using your NPSSO.",
                )

        elif playstation_username:
            user.account.loading_data = True
            user.account.save()
            get_account_id.send(user.pk, playstation_username)  # type: ignore
            return redirect("games")

        return render(request, self.template_name)

    def delete(self, request: HttpRequest) -> HttpResponse:
        Game.objects.filter(owner=self.request.user).delete()
        return render(request, "accounts/clear_library.html")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Retrieves and prepares context data for the settings view.

        This method extends the base context by adding the user's npsso token,
        the validity status of the npsso token, and the current theme from the session.

        Returns:
        - dict[str, Any]: A dictionary containing the context data.
        """
        context = super().get_context_data(**kwargs)

        context["theme"] = self.request.session.get("theme")
        context["playstation_username"] = self.request.user.account.playstation_username

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


@login_required
def upload_entitlements(request: HttpRequest) -> HttpResponse:
    try:
        json_file = request.FILES["json_file"]
        data = json.load(json_file)
    except Exception:
        messages.error(request, "Please upload a valid JSON file.")
        return redirect("settings")

    if request.user.id:
        entitlement_upload = EntitlementsUpload(user=request.user, data=data)

        entitlement_upload.save()

        if request.user.account.is_stale:
            load_entitlements.send(entitlement_upload.id)
        else:
            load_games.send(
                user_id=request.user.id, load_entitlements_id=entitlement_upload.id
            )

    return redirect("games")
