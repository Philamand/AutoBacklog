from django.urls import path
from .views import (
    dashboard,
    LibraryView,
    reset_filters,
    update_game,
    refresh_game_list,
    update_status,
    bulk_edit,
    search_titles,
    add_game,
)

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("games/<int:game_id>", update_game, name="update_game"),
    path("games/filters/reset/", reset_filters, name="reset_filters"),
    path("games/refresh/", refresh_game_list, name="refresh_game_list"),
    path("games/update_status/", update_status, name="update_status"),
    path("games/bulk_edit/", bulk_edit, name="bulk_edit"),
    path("games/search_titles/", search_titles, name="search_titles"),
    path("games/add_game/<str:title_id>/", add_game, name="add_game"),
    path("games/", LibraryView.as_view(), name="games"),
    path("games/<str:view>/", LibraryView.as_view()),
]
