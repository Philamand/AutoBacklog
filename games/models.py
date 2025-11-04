from django.db import models
from django.conf import settings

STATUS = [
    ("unp", "Unplayed"),
    ("unf", "Unfinished"),
    ("bea", "Beaten"),
    ("com", "Completed"),
    ("end", "Endless"),
    ("non", "None"),
]

OWNERSHIPS = [
    ("own", "Own"),
    ("wis", "Wishlist"),
    ("psp", "PS+"),
    ("pgc", "Game Catalog"),
]


class Game(models.Model):
    """
    Represents a game in the system.

    Attributes:
        owner (ForeignKey): The user who owns the game.
        title (CharField): The title of the game.
        psn_id (IntegerField): The PSN ID of the game.
        ps4 (BooleanField): Indicates if the game is available on PS4.
        ps5 (BooleanField): Indicates if the game is available on PS5.
        status (CharField): The current status of the game.
        priority (CharField): The priority of the game.
        ownership (CharField): The ownership status of the game.
        first_played (DateTimeField): The date and time the game was first played.
        last_played (DateTimeField): The date and time the game was last played.
        playtime (IntegerField): The total playtime of the game.
        active (BooleanField): Indicates if the game is active.
    """

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    psn_id = models.IntegerField(null=True, blank=True)
    ps4 = models.BooleanField(null=True, blank=True)
    ps5 = models.BooleanField(null=True, blank=True)
    status = models.CharField(max_length=3, choices=STATUS, default="unp")
    ownership = models.CharField(max_length=3, choices=OWNERSHIPS, default="own")
    active_date = models.DateTimeField(blank=True, null=True)
    first_played = models.DateTimeField(blank=True, null=True)
    last_played = models.DateTimeField(blank=True, null=True)
    playtime = models.IntegerField(blank=True, null=True)
    active = models.BooleanField(default=True)
    shelved = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.title


class GameTrophy(models.Model):
    """
    Represents a trophy associated with a game.

    Attributes:
        psn_id (IntegerField): The PSN ID of the game the trophy is associated with.
        name (CharField): The name of the trophy.
        trophy_id (CharField): The unique ID of the trophy.
        trophy_id_ps4 (CharField): The unique ID of the trophy for PS4.
        beaten_id (IntegerField): The ID of the trophy when it has been beaten.
    """

    psn_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=200)
    trophy_id = models.CharField(max_length=20, null=True, blank=True)
    trophy_id_ps4 = models.CharField(max_length=20, null=True, blank=True)
    beaten_id = models.IntegerField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "trophies"
        indexes = [models.Index(fields=["psn_id"])]

    def __str__(self) -> str:
        return self.name


class TitleId(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title_id = models.CharField(max_length=255)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.owner} - {self.game}"


class PlayStationTitle(models.Model):
    title_id = models.CharField(max_length=50, unique=True)
    concept_id = models.IntegerField(blank=True, null=True)
    name = models.CharField(max_length=250)
    content_id = models.CharField(max_length=250, blank=True, null=True)
    region = models.CharField(max_length=2, blank=True, null=True)
    publisher_id = models.CharField(max_length=6, blank=True, null=True)
