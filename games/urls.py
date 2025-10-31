from django.urls import path
from .views import (
    dashboard,
    LibraryView,
    reset_filters,
    update_game,
    refresh_game_list,
    update_status,
    bulk_edit,
)

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("games/<int:game_id>", update_game, name="update_game"),
    path("games/filters/reset/", reset_filters, name="reset_filters"),
    path("games/refresh/", refresh_game_list, name="refresh_game_list"),
    path("games/update_status/", update_status, name="update_status"),
    path("games/bulk_edit/", bulk_edit, name="bulk_edit"),
    path("games/", LibraryView.as_view(), name="games"),
    path("games/<str:view>/", LibraryView.as_view()),
]
