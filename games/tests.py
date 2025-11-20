from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import SafeText
from .models import Game, PlayStationTitle


class DashboardViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="TestUser", password="testpassword"
        )
        games = [
            Game(
                owner=self.user,
                title="God of War Ragnarök",
                ps4=True,
                ps5=True,
                status="unf",
                ownership="psp",
                first_played=timezone.now(),
                last_played=timezone.now(),
                playtime=600,
            ),
            Game(
                owner=self.user,
                title="Warhammer 40,000: Boltgun",
                ps4=True,
                ps5=True,
                status="unf",
                ownership="psp",
                first_played=timezone.now(),
                last_played=timezone.now(),
                playtime=600,
            ),
            Game(
                owner=self.user,
                title="Prince Of Persia: The Lost Crown",
                ps4=True,
                ps5=True,
                status="unf",
                ownership="psp",
                first_played=timezone.now(),
                last_played=timezone.now(),
                playtime=600,
                shelved=True,
            ),
            Game(
                owner=self.user,
                title="CRISIS CORE –FINAL FANTASY VII– REUNION",
                ps4=True,
                ps5=True,
                status="unf",
                ownership="psp",
                first_played=timezone.now(),
                last_played=timezone.now(),
                playtime=600,
            ),
            Game(
                owner=self.user,
                title="Marvel Spider-Man Remastered",
                ps4=True,
                ps5=True,
                status="unf",
                ownership="psp",
                first_played=timezone.now(),
                last_played=timezone.now(),
                playtime=600,
                deleted=True,
            ),
        ]
        Game.objects.bulk_create(games)

    def test_dashboard_not_logged(self):
        url = reverse("dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "index.html")
        self.assertTemplateNotUsed(response, "games/dashboard.html")

    def test_dashboard_logged(self):
        self.client.login(username="TestUser", password="testpassword")
        url = reverse("dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateNotUsed(response, "index.html")
        self.assertTemplateUsed(response, "games/dashboard.html")
        self.assertInHTML(
            '<div><i class="bi bi-controller fs-4 text-primary me-2"></i>CRISIS CORE –FINAL FANTASY VII– REUNION<i class="bi bi-gift ms-2"></i></div>',
            SafeText(response.content.decode()),
        )
        self.assertNotInHTML(
            '<div><i class="bi bi-controller fs-4 text-primary me-2"></i>Prince Of Persia: The Lost Crown<i class="bi bi-gift ms-2"></i></div>',
            SafeText(response.content.decode()),
        )
        self.assertNotInHTML(
            '<div><i class="bi bi-controller fs-4 text-primary me-2"></i>Marvel Spider-Man Remastered<i class="bi bi-gift ms-2"></i></div>',
            SafeText(response.content.decode()),
        )


class GameDetailViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="TestUser", password="testpassword"
        )
        self.user2 = User.objects.create_user(
            username="TestUser2", password="testpassword2"
        )

        games = [
            Game(
                owner=self.user,
                title="God of War Ragnarök",
                ps4=True,
                ps5=True,
                status="unf",
                ownership="psp",
                first_played=timezone.now(),
                last_played=timezone.now(),
                playtime=600,
            ),
            Game(
                owner=self.user,
                title="Warhammer 40,000: Boltgun",
                ps4=True,
                ps5=True,
                status="unf",
                ownership="psp",
                first_played=timezone.now(),
                last_played=timezone.now(),
                playtime=600,
            ),
            Game(
                owner=self.user,
                title="Prince Of Persia: The Lost Crown",
                ps4=True,
                ps5=True,
                status="unf",
                ownership="psp",
                first_played=timezone.now(),
                last_played=timezone.now(),
                playtime=600,
                shelved=True,
            ),
        ]

        Game.objects.bulk_create(games)

        self.usergame = Game(
            owner=self.user,
            title="CRISIS CORE –FINAL FANTASY VII– REUNION",
            ps4=True,
            ps5=True,
            status="unf",
            ownership="psp",
            first_played=timezone.now(),
            last_played=timezone.now(),
            playtime=600,
        )

        self.usergame.save()

        self.user2game = Game(
            owner=self.user2,
            title="CRISIS CORE –FINAL FANTASY VII– REUNION",
            ps4=True,
            ps5=True,
            status="unf",
            ownership="psp",
            first_played=timezone.now(),
            last_played=timezone.now(),
            playtime=600,
        )

        self.user2game.save()

        self.client.login(username="TestUser", password="testpassword")

    def test_unauthorized(self):
        url = reverse("game_detail", kwargs={"pk": self.user2game.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_authorized(self):
        url = reverse("game_detail", kwargs={"pk": self.usergame.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class GameUpdateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="TestUser", password="testpassword"
        )
        self.user2 = User.objects.create_user(
            username="TestUser2", password="testpassword2"
        )

        games = [
            Game(
                owner=self.user,
                title="God of War Ragnarök",
                ps4=True,
                ps5=True,
                status="unf",
                ownership="psp",
                first_played=timezone.now(),
                last_played=timezone.now(),
                playtime=600,
            ),
            Game(
                owner=self.user,
                title="Warhammer 40,000: Boltgun",
                ps4=True,
                ps5=True,
                status="unf",
                ownership="psp",
                first_played=timezone.now(),
                last_played=timezone.now(),
                playtime=600,
            ),
            Game(
                owner=self.user,
                title="Prince Of Persia: The Lost Crown",
                ps4=True,
                ps5=True,
                status="unf",
                ownership="psp",
                first_played=timezone.now(),
                last_played=timezone.now(),
                playtime=600,
                shelved=True,
            ),
        ]

        Game.objects.bulk_create(games)

        self.usergame = Game(
            owner=self.user,
            title="CRISIS CORE –FINAL FANTASY VII– REUNION",
            ps4=True,
            ps5=True,
            status="unf",
            ownership="psp",
            first_played=timezone.now(),
            last_played=timezone.now(),
            playtime=600,
        )

        self.usergame.save()

        self.user2game = Game(
            owner=self.user2,
            title="CRISIS CORE –FINAL FANTASY VII– REUNION",
            ps4=True,
            ps5=True,
            status="unf",
            ownership="psp",
            first_played=timezone.now(),
            last_played=timezone.now(),
            playtime=600,
        )

        self.user2game.save()

        self.client.login(username="TestUser", password="testpassword")

    def test_unauthorized(self):
        url = reverse("update_game", kwargs={"pk": self.user2game.id})
        response = self.client.post(
            url,
            {
                "title": "CRISIS CORE –FINAL FANTASY VII– REUNION",
                "ps4": True,
                "ps5": True,
                "status": "bea",
                "ownership": "psp",
                "active": True,
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_authorized(self):
        url = reverse("update_game", kwargs={"pk": self.usergame.id})
        game = Game.objects.get(pk=self.usergame.id)
        initial_track = game.track

        response = self.client.post(
            url,
            {
                "title": "CRISIS CORE –FINAL FANTASY VII– REUNION",
                "ps4": True,
                "ps5": True,
                "status": "bea",
                "ownership": "psp",
                "active": True,
            },
        )

        game = Game.objects.get(pk=self.usergame.id)
        final_track = game.track

        self.assertEqual(response.status_code, 302)
        self.assertTrue(initial_track)
        self.assertFalse(final_track)


class RemoveGameViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="TestUser", password="testpassword"
        )
        self.user2 = User.objects.create_user(
            username="TestUser2", password="testpassword2"
        )

        games = [
            Game(
                owner=self.user,
                title="God of War Ragnarök",
                ps4=True,
                ps5=True,
                status="unf",
                ownership="psp",
                first_played=timezone.now(),
                last_played=timezone.now(),
                playtime=600,
            ),
            Game(
                owner=self.user,
                title="Warhammer 40,000: Boltgun",
                ps4=True,
                ps5=True,
                status="unf",
                ownership="psp",
                first_played=timezone.now(),
                last_played=timezone.now(),
                playtime=600,
            ),
            Game(
                owner=self.user,
                title="Prince Of Persia: The Lost Crown",
                ps4=True,
                ps5=True,
                status="unf",
                ownership="psp",
                first_played=timezone.now(),
                last_played=timezone.now(),
                playtime=600,
                shelved=True,
            ),
        ]

        Game.objects.bulk_create(games)

        self.usergame = Game(
            owner=self.user,
            title="CRISIS CORE –FINAL FANTASY VII– REUNION",
            ps4=True,
            ps5=True,
            status="unf",
            ownership="psp",
            first_played=timezone.now(),
            last_played=timezone.now(),
            playtime=600,
        )

        self.usergame.save()

        self.user2game = Game(
            owner=self.user2,
            title="CRISIS CORE –FINAL FANTASY VII– REUNION",
            ps4=True,
            ps5=True,
            status="unf",
            ownership="psp",
            first_played=timezone.now(),
            last_played=timezone.now(),
            playtime=600,
        )

        self.user2game.save()

        self.client.login(username="TestUser", password="testpassword")

    def test_unauthorized(self):
        url = reverse("remove_game", kwargs={"pk": self.user2game.id})
        response = self.client.patch(url, "action=shelf")
        self.assertEqual(response.status_code, 403)

    def test_authorized_shelf(self):
        url = reverse("remove_game", kwargs={"pk": self.usergame.id})
        self.assertEqual(self.usergame.shelved, False)
        response = self.client.patch(
            url,
            "action=shelf",
        )
        self.assertEqual(response.status_code, 200)
        game = Game.objects.get(id=self.usergame.id)
        self.assertEqual(game.shelved, True)

    def test_authorized_delete(self):
        url = reverse("remove_game", kwargs={"pk": self.usergame.id})
        self.assertEqual(self.usergame.deleted, False)
        response = self.client.patch(
            url,
            "action=delete",
        )
        self.assertEqual(response.status_code, 200)
        game = Game.objects.get(id=self.usergame.id)
        self.assertEqual(game.deleted, True)

    def test_bad_request(self):
        url = reverse("remove_game", kwargs={"pk": self.usergame.id})
        response = self.client.patch(
            url,
            "action=shnefl",
        )
        self.assertEqual(response.status_code, 400)


class ResetFiltersViewTests(TestCase):
    def setUp(self):
        self.url = reverse("reset_filters")

        self.user = User.objects.create_user(
            username="TestUser", password="testpassword"
        )
        self.client.login(username="TestUser", password="testpassword")

    def test_main(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "games/filters/main.html")

    def test_status(self):
        response = self.client.post(self.url, {"reset": "status"})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "games/filters/status.html")

    def test_platforms(self):
        response = self.client.post(self.url, {"reset": "platforms"})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "games/filters/platforms.html")

    def test_ownership(self):
        response = self.client.post(self.url, {"reset": "ownership"})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "games/filters/ownership.html")

    def test_active(self):
        response = self.client.post(self.url, {"reset": "active"})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "games/filters/active.html")


class BulkEditViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="TestUser", password="testpassword"
        )

        games = []

        for i in range(100):
            games.append(
                Game(
                    owner=self.user,
                    title=f"Game {str(i)}",
                    ps4=True,
                    ps5=True,
                    status="unf",
                    ownership="psp",
                    first_played=timezone.now(),
                    last_played=timezone.now(),
                    playtime=600,
                )
            )

        Game.objects.bulk_create(games)

        self.client.login(username="TestUser", password="testpassword")

    def test_edit_shelf_view(self):
        games = Game.objects.filter(owner=self.user).exclude(shelved=True)
        self.assertEqual(len(games), 100)

        url = reverse("bulk_edit")
        response = self.client.post(
            url,
            {
                "action": "shelf",
                "games": [games[0].id, games[1].id, games[2].id, games[3].id],
            },
        )

        games = Game.objects.filter(owner=self.user).exclude(shelved=True)
        shelved = Game.objects.filter(owner=self.user).filter(shelved=True)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(games), 96)
        self.assertEqual(len(shelved), 4)

    def test_edit_delete_view(self):
        games = Game.objects.filter(owner=self.user).exclude(deleted=True)
        self.assertEqual(len(games), 100)

        url = reverse("bulk_edit")
        response = self.client.post(
            url,
            {
                "action": "delete",
                "games": [games[0].id, games[1].id, games[2].id, games[3].id],
            },
        )

        games = Game.objects.filter(owner=self.user).exclude(deleted=True)
        deleted = Game.objects.filter(owner=self.user).filter(deleted=True)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(games), 96)
        self.assertEqual(len(deleted), 4)

    def test_edit_incorrect_view(self):
        games = (
            Game.objects.filter(owner=self.user)
            .exclude(shelved=True)
            .exclude(deleted=True)
        )
        self.assertEqual(len(games), 100)

        url = reverse("bulk_edit")
        response = self.client.post(
            url,
            {
                "action": "",
                "games": [games[0].id, games[1].id, games[2].id, games[3].id],
            },
        )

        games = (
            Game.objects.filter(owner=self.user)
            .exclude(shelved=True)
            .exclude(deleted=True)
        )
        shelved = (
            Game.objects.filter(owner=self.user)
            .filter(shelved=True)
            .exclude(deleted=True)
        )
        deleted = (
            Game.objects.filter(owner=self.user)
            .exclude(shelved=True)
            .filter(deleted=True)
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(games), 100)
        self.assertEqual(len(shelved), 0)
        self.assertEqual(len(deleted), 0)


class LibraryViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="TestUser", password="testpassword"
        )

        games = []

        for i in range(100):
            if i % 10 == 0:
                games.append(
                    Game(
                        owner=self.user,
                        title=f"Unwanted Game {str(i)}",
                        ps4=True,
                        ps5=True,
                        status="unf",
                        ownership="psp",
                        first_played=timezone.now(),
                        last_played=timezone.now(),
                        playtime=600,
                        shelved=True,
                    )
                )
            else:
                games.append(
                    Game(
                        owner=self.user,
                        title=f"Game {str(i)}",
                        ps4=True,
                        ps5=True,
                        status="unf",
                        ownership="psp",
                        first_played=timezone.now(),
                        last_played=timezone.now(),
                        playtime=600,
                    )
                )

        Game.objects.bulk_create(games)

        self.client.login(username="TestUser", password="testpassword")

    def test_library_view(self):
        url = reverse("games")
        response = self.client.get(url)

        games = (
            Game.objects.filter(owner=self.user)
            .exclude(shelved=True)
            .order_by("title")[:25]
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["games"]), list(games))

    def test_library_htmx(self):
        url = reverse("games") + "?page=2"
        response = self.client.get(url, headers={"HX-Request": True})

        games = (
            Game.objects.filter(owner=self.user)
            .exclude(shelved=True)
            .order_by("title")[25:50]
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["games"]), list(games))
        self.assertInHTML(
            '<div id="game_length" hx-swap-oob="true">90</div>',
            SafeText(response.content.decode()),
        )
        self.assertTemplateUsed("games/game_container.html")
        self.assertTemplateNotUsed("games/game_list.html")

    def test_shelf_view(self):
        url = reverse("games") + "shelf/"
        response = self.client.get(url)

        games = (
            Game.objects.filter(owner=self.user)
            .filter(shelved=True)
            .order_by("title")[:25]
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["games"]), list(games))


class SearchTitlesViewTest(TestCase):
    def setUp(self):
        self.url = reverse("search_titles")
        self.user = User.objects.create_user(
            username="TestUser", password="testpassword"
        )
        self.client.login(username="TestUser", password="testpassword")

        PlayStationTitle.objects.create(
            title_id="PPSA04312_00",
            concept_id=10000689,
            name="The Dungeon of Naheulbeuk: the Amulet of Chaos",
            region="EP",
        )

        PlayStationTitle.objects.create(
            title_id="PPSA05259_00", concept_id=231761, name="Diablo IV", region="EP"
        )

    def test_search_titles_view(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "games/components/search_titles.html")

    def test_search_titles_post(self):
        response = self.client.post(self.url, {"search": "naheulbeuk"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["titles"]), 1)


class AddGameViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="TestUser", password="testpassword"
        )
        self.client.login(username="TestUser", password="testpassword")

        PlayStationTitle.objects.create(
            title_id="PPSA04312_00",
            concept_id=10000689,
            name="The Dungeon of Naheulbeuk: the Amulet of Chaos",
            region="EP",
        )

        PlayStationTitle.objects.create(
            title_id="PPSA05259_00", concept_id=231761, name="Diablo IV", region="EP"
        )

        Game.objects.create(owner=self.user, title="Diablo IV", psn_id=231761)

    def test_add_game_view(self):
        url = reverse("add_game", kwargs={"title_id": "PPSA04312_00"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["title_id"], "PPSA04312_00")
        self.assertTemplateUsed(response, "games/components/add_game.html")

    def test_add_game_post(self):
        url = reverse("add_game", kwargs={"title_id": "PPSA04312_00"})

        first_games_count = Game.objects.filter(owner=self.user).count()

        response = self.client.post(
            url,
            {
                "title": "The Dungeon of Naheulbeuk: the Amulet of Chaos",
                "ps4": True,
                "ps5": True,
                "status": "unp",
                "ownership": "phy",
            },
        )

        final_games_count = Game.objects.filter(owner=self.user).count()

        self.assertEqual(response.status_code, 200)
        self.assertIn("HX-Redirect", response.headers)
        self.assertEqual(first_games_count, 1)
        self.assertEqual(final_games_count, 2)

    def test_add_game_already_in_library(self):
        url = reverse("add_game", kwargs={"title_id": "PPSA05259_00"})

        first_games_count = Game.objects.filter(owner=self.user).count()

        response = self.client.post(
            url,
            {
                "title": "Diablo IV",
                "ps4": True,
                "ps5": True,
                "status": "unp",
                "ownership": "phy",
            },
        )

        final_games_count = Game.objects.filter(owner=self.user).count()

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("HX-Redirect", response.headers)
        self.assertFormError(
            form=response.context["form"],
            field=None,
            errors=["Diablo IV is already in your library."],
        )  # type: ignore
        self.assertEqual(first_games_count, 1)
        self.assertEqual(final_games_count, 1)
