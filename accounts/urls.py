from django.urls import include, path
from . import views

urlpatterns = [
    path("", include("allauth.urls")),
    path("settings/", views.SettingsView.as_view(), name="settings"),
    path("toggle/", views.toggle_theme, name="toggle_theme")
]
