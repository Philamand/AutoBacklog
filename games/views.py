from typing import Any
from django.db.models.base import Model as Model
from django.forms import BaseModelForm
from django.http import HttpRequest, HttpResponse, QueryDict
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, UpdateView
from django.db.models import F
from django.db.models.query import QuerySet
from django.shortcuts import redirect, render
from .models import Game, PlayStationTitle
from .forms import AddGameForm
from .tasks import load_games


def dashboard(request: HttpRequest) -> HttpResponse:
    """
    Renders the dashboard page for authenticated users, displaying a summary of their games.

    This view checks if the user is authenticated. If so, it fetches the user's games,
    excluding those with a 'she' priority, and orders them by the last played date.
    It then calculates counts for games grouped by platform (PS4, PS5) and status
    (unplayed, unfinished, beaten, completed, and shelved). These counts and the
    top three recently played games are passed to the 'dashboard.html' template for
    display, along with the user's theme preference.

    If the user is not authenticated, it renders the 'index.html' page.

    Parameters:
    - request: The HTTP request object.

    Returns:
    - A rendered 'dashboard.html' page with the user's game data and theme, or
      'index.html' if the user is not authenticated.
    """
    if request.user.is_authenticated:
        base_query = (
            Game.objects.filter(owner=request.user)
            .exclude(shelved=True)
            .exclude(deleted=True)
        )
        games = base_query.order_by(F("last_played").desc(nulls_last=True))[:3]
        count = {}
        count["total"] = base_query.count
        count["ps4"] = base_query.filter(ps4=True).count
        count["ps5"] = base_query.filter(ps5=True).count
        count["unp"] = base_query.filter(status="unp").count
        count["unf"] = base_query.filter(status="unf").count
        count["bea"] = base_query.filter(status="bea").count
        count["com"] = base_query.filter(status="com").count
        count["she"] = (
            Game.objects.filter(owner=request.user).filter(shelved=True).count
        )

        theme = request.session.get("theme")
        return render(
            request,
            "games/dashboard.html",
            {"games": games, "count": count, "theme": theme},
        )
    return render(request, "index.html")


@login_required
@require_http_methods(["PATCH"])
def remove_game(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Updates the game's priority or status based on the action specified in the request.
    Requires the game to be owned by the requesting user.
    Supports 'shelf' action to toggle game priority, 'beat' to set game status to 'beaten',
    and 'unfinished' to set game status to 'unfinished'.
    Returns an updated game card template for the 'beat' and 'unfinished' actions,
    or a 200 status code for the 'shelf' action.
    Returns a 403 status code if the user is not the owner of the game,
    or a 400 status code for an invalid action.
    """
    game = get_object_or_404(Game, pk=pk)

    if game.owner != request.user:
        return HttpResponse(status=403)

    action = QueryDict(request.body).get("action")
    if action == "shelf":
        game.shelved = not game.shelved
        game.save()
        return HttpResponse(status=200)
    elif action == "delete":
        game.deleted = not game.deleted
        game.save()
        return HttpResponse(status=200)
    return HttpResponse(status=400)


class GameDetailView(LoginRequiredMixin, DetailView):
    model = Game
    template_name = "games/components/game_card.html"
    context_object_name = "game"

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        obj = self.get_object()

        if obj.owner != request.user:
            return HttpResponse(status=403)

        return super().dispatch(request, *args, **kwargs)


class GameUpdateView(LoginRequiredMixin, UpdateView):
    model = Game
    fields = ["title", "ps4", "ps5", "status", "ownership", "active"]
    template_name = "games/game_update_form.html"

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        obj = self.get_object()

        if obj.owner != request.user:
            return HttpResponse(status=403)

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        form.instance.track = False
        return super().form_valid(form)


@login_required
@require_POST
def reset_filters(request: HttpRequest) -> HttpResponse:
    """
    Resets the filters in the session to their default values based on the filter type specified in the request.
    Supports resetting status, platforms, ownership, and active filters individually or all filters at once.
    Returns a rendered filter template corresponding to the reset filter type or the main filter template if all filters are reset.
    """
    filters = request.session.get(
        "filters",
        {
            "status": ["unp", "unf", "bea", "com", "end"],
            "platform": "all",
            "ownership": ["own", "phy", "psp", "pgc"],
            "active": "all",
        },
    )
    reset = QueryDict(request.body).get("reset")
    if reset == "status":
        filters["status"] = ["unp", "unf", "bea", "com", "end"]
        request.session["filters"] = filters
        return render(request, "games/filters/status.html", {"filters": filters})
    elif reset == "platforms":
        filters["platform"] = "all"
        request.session["filters"] = filters
        return render(request, "games/filters/platforms.html", {"filters": filters})
    elif reset == "ownership":
        filters["ownership"] = ["own", "phy", "psp", "pgc"]
        request.session["filters"] = filters
        return render(request, "games/filters/ownership.html", {"filters": filters})
    elif reset == "active":
        filters["active"] = "all"
        request.session["filters"] = filters
        return render(request, "games/filters/active.html", {"filters": filters})

    filters = {
        "status": ["unp", "unf", "bea", "com", "end"],
        "platform": "all",
        "ownership": ["own", "psp", "pgc"],
        "active": "all",
    }
    request.session["filters"] = filters

    return render(request, "games/filters/main.html", {"filters": filters})


@login_required
def refresh_game_list(request: HttpRequest) -> HttpResponse:
    """
    Refreshes the user's game list by triggering a background task to load games.

    This view checks if the user's game list is stale and not currently loading.
    If so, it marks the game list as loading, saves the user's account status,
    and triggers the 'load_games' task asynchronously to update the game list.
    Finally, it renders the loading_data.html template to indicate the update process.

    Parameters:
    - request (HttpRequest): The HTTP request object.

    Returns:
    - HttpResponse: The rendered loading_data.html template.
    """
    if not request.user.account.loading_data and request.user.account.is_stale:
        request.user.account.loading_data = True
        request.user.account.save()
        load_games.send(request.user.id)  # type: ignore

    return render(request, "games/components/loading_data.html")


@login_required
def update_status(request: HttpRequest) -> HttpResponse:
    """
    Handles the update status request for the user's account.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: The HTTP response object.
    """
    response = HttpResponse()
    user = User.objects.prefetch_related("account").get(pk=request.user.id)
    if user.account.loading_data:
        response.status_code = 200
        return response

    if not user.account.account_id:
        messages.error(
            request,
            "PlayStation account not found. Please make sure that your account is public.",
        )
        response["HX-Redirect"] = "/accounts/settings/"
    else:
        response["HX-Redirect"] = "/games/"

    return response


@login_required
@require_POST
def bulk_edit(request: HttpRequest) -> HttpResponse:
    """
    Handles the bulk edit request for games.

    Parameters:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: The HTTP response object after redirecting to the games page.
    """
    action = request.POST.get("action")
    if action in [
        "shelf",
        "delete",
        "unp",
        "unf",
        "bea",
        "com",
        "end",
        "own",
        "phy",
        "psp",
        "pgc",
        "active",
        "inactive",
    ]:
        game_ids = []
        post_games = request.POST.getlist("games")
        if post_games:
            for id in post_games:
                game_ids.append(int(id))

        games = Game.objects.filter(id__in=game_ids)

        for game in games:
            if action in ["unp", "unf", "bea", "com", "end"]:
                game.status = action
            elif action in ["own", "phy", "psp", "pgc"]:
                game.ownership = action
            elif action == "active":
                game.active = True
            elif action == "inactive":
                game.active = False
            elif action == "shelf":
                game.shelved = not game.shelved
            else:
                game.deleted = not game.deleted

        Game.objects.bulk_update(
            games, ["status", "ownership", "active", "shelved", "deleted"]
        )

    return redirect("/games/")


class LibraryView(LoginRequiredMixin, ListView):
    """
    LibraryView is a view that displays a list of games owned by the user.
    It allows filtering and sorting of the games based on various criteria.
    """

    model = Game
    context_object_name = "games"
    ordering = ["title"]
    paginate_by = 25

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Handles GET requests to the view, applying filters and sorting to the game list.
        Updates session data with the current filters and sort order.
        """
        filters = self.request.session.get(
            "filters",
            {
                "status": ["unp", "unf", "bea", "com", "end"],
                "platform": "all",
                "ownership": ["own", "phy", "psp", "pgc"],
                "active": "all",
            },
        )

        sort = self.request.session.get("sort", "name")
        if self.request.GET.get("sort"):
            sort = self.request.GET.get("sort")
        self.request.session["sort"] = sort

        status = []

        if self.request.GET.get("unp"):
            status.append("unp")
        if self.request.GET.get("unf"):
            status.append("unf")
        if self.request.GET.get("bea"):
            status.append("bea")
        if self.request.GET.get("com"):
            status.append("com")
        if self.request.GET.get("end"):
            status.append("end")

        if status != []:
            filters["status"] = status

        if self.request.GET.get("ps5"):
            if self.request.GET.get("ps4"):
                filters["platform"] = "all"
            else:
                filters["platform"] = "ps5"
        elif self.request.GET.get("ps4"):
            filters["platform"] = "ps4"

        own = []
        if self.request.GET.get("own"):
            own.append("own")
        if self.request.GET.get("phy"):
            own.append("phy")
        if self.request.GET.get("psp"):
            own.append("psp")
        if self.request.GET.get("pgc"):
            own.append("pgc")
        if own != []:
            filters["ownership"] = own

        if self.request.GET.get("active"):
            if self.request.GET.get("inactive"):
                filters["active"] = "all"
            else:
                filters["active"] = "active"
        elif self.request.GET.get("inactive"):
            filters["active"] = "inactive"

        self.request.session["filters"] = filters
        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[Any]:
        """
        Returns a queryset of games filtered and sorted based on the current session filters.
        Filters games by status, ownership, platform, and activity.
        Applies search and sort order to the queryset.
        """
        filters = self.request.session["filters"]
        games = (
            super().get_queryset().filter(owner=self.request.user).exclude(deleted=True)
        )

        if self.request.session["sort"] == "name":
            games = games.order_by("title")
        elif self.request.session["sort"] == "-name":
            games = games.order_by("-title")
        elif self.request.session["sort"] == "bought":
            games = games.order_by(F("active_date").desc(nulls_last=True), "-id")
        elif self.request.session["sort"] == "recent":
            games = games.order_by(
                F("last_played").desc(nulls_last=True), "-active_date"
            )

        if self.kwargs.get("view") == "shelf":
            games = games.filter(shelved=True)
        else:
            games = games.filter(shelved=False)

        games = games.filter(status__in=filters["status"])
        games = games.filter(ownership__in=filters["ownership"])

        if filters["platform"] in ["ps4", "ps5", "ps4o", "ps5o"]:
            if filters["platform"] == "ps5":
                games = games.filter(ps5=True)
            elif filters["platform"] == "ps5o":
                games = games.filter(ps5=True, ps4=False)
            elif filters["platform"] == "ps4o":
                games = games.filter(ps5=False, ps4=True)
            else:
                games = games.filter(ps4=True)

        if filters["active"] in ["active", "inactive"]:
            games = games.filter(active=filters["active"] == "active")

        search = self.request.GET.get("search")
        if search:
            games = games.filter(title__icontains=search)

        return games

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Adds additional context data to the view, including user information, sort order,
        and whether the request is an HTMX request. Also includes filters if not an HTMX request.
        """
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        context["sort"] = self.request.session.get("sort", "name")

        if self.kwargs.get("view") == "shelf":
            context["shelf"] = True

        if self.kwargs.get("view") == "edit":
            context["edit"] = True

        if self.request.headers.get("HX-Request") and not self.request.headers.get(
            "HX-Boosted"
        ):
            context["htmx"] = True
        else:
            context["filters"] = self.request.session.get("filters")

        if self.request.session.get("theme"):
            context["theme"] = self.request.session.get("theme")

        return context

    def get_template_names(self) -> list[str]:
        """
        Returns the template name(s) to be used for rendering the view.
        If the request is an HTMX request, returns a partial template for game containers.
        Otherwise, returns the default template names for the ListView.
        """
        if self.request.headers.get("HX-Request") and not self.request.headers.get(
            "HX-Boosted"
        ):
            return ["games/game_container.html"]
        return super().get_template_names()


@login_required
def search_titles(request: HttpRequest) -> HttpResponse:
    """
    Search for PlayStation titles matching a user-provided query.

    This view handles both GET and POST requests. On a GET request it renders the
    search form template ``games/components/search_titles.html``. On a POST
    request it extracts the ``search`` term from the submitted form data,
    filters ``PlayStationTitle`` objects whose ``name`` contains the term (case‑insensitive)
    and belong to the ``EP`` region, orders the results by descending ``id``,
    and returns the first five matches rendered with the template
    ``games/components/search_titles_result.html``.

    Args:
        request (HttpRequest): The incoming HTTP request, expected to be a
            ``POST`` with a ``search`` field or a ``GET`` to display the form.

    Returns:
        HttpResponse: Rendered HTML containing either the search form or the
        top five matching titles.
    """
    if request.method == "POST":
        search = request.POST.get("search")
        titles = (
            PlayStationTitle.objects.filter(name__icontains=search)
            .filter(region="EP")
            .order_by("-id")[:5]
        )

        return render(
            request, "games/components/search_titles_result.html", {"titles": titles}
        )

    return render(request, "games/components/search_titles.html")


@login_required
def add_game(request: HttpRequest, title_id: str) -> HttpResponse:
    """
    Add a PlayStation title to the authenticated user's game library.

    This view requires the user to be logged in. It retrieves a
    ``PlayStationTitle`` instance identified by ``title_id``. For a ``GET``
    request it determines whether the title belongs to the PS4 or PS5 platform
    (based on the presence of ``"PPSA"`` in the identifier) and pre‑populates an
    ``AddGameForm`` with the title name, platform flags, and a default ownership
    value of ``"phy"``. The populated form is rendered using the template
    ``games/components/add_game.html``.

    For a ``POST`` request the submitted form data is validated. If the form is
    valid, the view checks whether the user already owns a ``Game`` with the same
    PlayStation Network identifier (``psn_id``). If the title is not already in the
    library, a new ``Game`` instance is created (without committing immediately),
    the current user is set as the owner, the ``psn_id`` is assigned from the
    corresponding ``PlayStationTitle``'s ``concept_id``, and the instance is saved.
    A successful addition triggers an ``HX-Redirect`` header pointing to ``/games/``
    to navigate the user back to the games list.

    If the title already exists in the user's library, a non-field error is added
    to the form indicating the duplication, and the form is re-rendered for the
    user to correct.

    Args:
        request (HttpRequest): The incoming request, either ``GET`` to display the
            form or ``POST`` to process a submission.
        title_id (str): The unique identifier of the ``PlayStationTitle`` to be
            added.

    Returns:
        HttpResponse: Either the rendered ``add_game.html`` template with the form
        (for ``GET`` or invalid submissions) or a response containing an
        ``HX-Redirect`` header to ``/games/`` upon successful addition.
    """
    title = get_object_or_404(PlayStationTitle, title_id=title_id)

    if request.method == "POST":
        form = AddGameForm(request.POST)

        if form.is_valid():
            already_in_library = (
                Game.objects.filter(owner=request.user)
                .filter(psn_id=title.concept_id)
                .count()
            )
            if already_in_library == 0:
                new_game = form.save(commit=False)
                new_game.owner = request.user
                new_game.psn_id = title.concept_id
                new_game.save()

                response = HttpResponse()
                response["HX-Redirect"] = "/games/"
                return response
            else:
                form.add_error(None, f"{title.name} is already in your library.")

    else:
        ps4 = False
        ps5 = False

        if "PPSA" in title_id:
            ps5 = True
        else:
            ps4 = True

        form = AddGameForm(
            initial={"title": title.name, "ps4": ps4, "ps5": ps5, "ownership": "phy"}
        )

    return render(
        request, "games/components/add_game.html", {"form": form, "title_id": title_id}
    )
