import dramatiq
import httpx
import asyncio
import os
import time
from cryptography.fernet import Fernet
from asyncio import Semaphore
from pydantic import BaseModel
from datetime import datetime, timedelta
from psnawp_api import PSNAWP
from psnawp_api.core.psnawp_exceptions import PSNAWPAuthenticationError
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Game, GameTrophy, TitleId


class Trophy(BaseModel):
    trophyId: int
    trophyHidden: bool
    earned: bool
    progress: str = "100/100"
    progressRate: int = 100
    progressDateTime: datetime | None = None
    earnedDateTime: datetime | None = None
    trophyType: str
    trophyRare: int
    trophyEarnedRate: str


class RarestTrophies(BaseModel):
    trophyId: int
    trophyHidden: bool
    earned: bool
    earnedDateTime: datetime | None = None
    trophyType: str
    trophyRare: int
    trophyEarnedRate: str


class TrophiesResults(BaseModel):
    conceptId: str | None = None
    trophySetVersion: str
    hasTrophyGroups: bool
    lastUpdatedDateTime: datetime
    trophies: list[Trophy]
    rarestTrophies: list[Trophy] | None = None
    totalItemCount: int
    nextOffset: int | None = None
    previousOffset: int | None = None


class DefinedTrophies(BaseModel):
    bronze: int
    silver: int
    gold: int
    platinum: int


class TrophyTitles(BaseModel):
    npServiceName: str
    npCommunicationId: str
    trophyTitleName: str
    trophyTitleDetail: str | None = None
    trophyTitleIconUrl: str
    hasTrophyGroups: bool
    rarestTrophies: list[Trophy]
    progress: int
    earnedTrophies: DefinedTrophies
    definedTrophies: DefinedTrophies
    notEarnedTrophyIds: list[int]
    lastUpdatedDateTime: datetime


class Titles(BaseModel):
    npTitleId: str
    trophyTitles: list[TrophyTitles]


class TitleResult(BaseModel):
    titles: list[Titles]


class ConceptMeta(BaseModel):
    """Metadata about the game concept."""

    conceptId: str
    iconUrl: str | None = None
    minimumAge: int | None = None
    name: str | None = None


class EntitlementAttribute(BaseModel):
    """Represents an entitlement attribute for a game entitlement."""

    entitlementKeyFlag: bool
    placeholderFlag: bool
    platformId: str


class GameMeta(BaseModel):
    """Metadata about the game."""

    iconUrl: str
    name: str
    packageType: str
    type: str


class RewardMeta(BaseModel):
    """Metadata about rewards for the entitlement."""

    retentionPolicy: int | None = None
    rewardServiceType: int = 5


class TitleMeta(BaseModel):
    """Metadata about the game title."""

    imageUrl: str | None = None
    name: str
    titleId: str


class GameEntitlement(BaseModel):
    """Represents a single game entitlement entry."""

    activeDate: datetime
    activeFlag: bool
    conceptMeta: ConceptMeta
    consumedCount: int
    entitlementAttributes: list[EntitlementAttribute]
    entitlementType: int
    featureType: int
    gameMeta: GameMeta
    id: str
    isBeta: bool | None = None
    isConsumable: bool
    isGame: bool | None = None
    isSubscription: bool
    preorderFlag: bool
    preorderPlaceholderFlag: bool
    productId: str
    remainingCount: int
    revisionId: int
    rewardMeta: RewardMeta
    serviceType: int | None = None
    skuId: str
    titleMeta: TitleMeta


class EntitlementsResult(BaseModel):
    revisionId: int
    start: int
    totalResults: int
    entitlements: list[GameEntitlement]


class TitleStats(BaseModel):
    """A class that represents a PlayStation Video Game Play Time Stats."""

    category: str | None
    firstPlayedDateTime: datetime | None = None
    imageUrl: str
    lastPlayedDateTime: datetime | None = None
    name: str | None = None
    playCount: int | None = None
    playDuration: timedelta | None = None
    titleId: str | None = None


class TitleStatsResult(BaseModel):
    titles: list[TitleStats]
    nextOffset: int | None
    previousOffset: int
    totalItemCount: int


async def fetch_with_rate_limit(titleIds, access_token, max_limit=5):
    semaphore = Semaphore(max_limit)

    async def fetch(titleId):
        async with semaphore:
            response = await make_psn_request(
                f"https://m.np.playstation.com/api/trophy/v1/users/me/titles/trophyTitles?npTitleIds={titleId}&includeNotEarnedTrophyIds=true",
                access_token,
            )
            dta = TitleResult(**response)
            return dta

    tasks = [fetch(titleId) for titleId in titleIds]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return results


async def make_psn_request(url: str, access_token: str):
    """
    Asynchronously makes a request to the PlayStation Network API.

    Parameters:
        url (str): The URL to make the request to.
        access_token (str): The access token to use for authentication.

    Returns:
        dict: The JSON response from the API.
    """
    async with httpx.AsyncClient() as httpxClient:
        response = await httpxClient.get(
            url,
            headers={
                "Authorization": "Bearer " + access_token,
                "Content-Type": "application/json",
            },
        )
        return response.json()


async def get_title_stats(access_token: str, last_played: datetime) -> list[TitleStats]:
    """
    Asynchronously retrieves title statistics from the PlayStation Network API.

    Parameters:
        access_token (str): The access token to use for authentication.

    Returns:
        list[TitleStats]: A list of TitleStats objects representing the statistics of the titles.
    """
    titleStats: list[TitleStats] = []
    offset = 0
    while offset is not None:
        response = await make_psn_request(
            f"https://m.np.playstation.com/api/gamelist/v2/users/me/titles?limit=100&offset={str(offset)}",
            access_token,
        )
        titleStatsResults = TitleStatsResult(**response)
        offset = titleStatsResults.nextOffset
        for title in titleStatsResults.titles:
            if (
                last_played
                and title.lastPlayedDateTime
                and title.lastPlayedDateTime <= last_played
            ):
                offset = None
                break
            else:
                titleStats.append(title)

    return titleStats


async def get_entitlements(
    access_token: str, user: User, entitlements_offset: int
) -> tuple[dict[str, Game], dict[str, str], int]:
    """
    Asynchronously retrieves game entitlements and title IDs from the PlayStation Network API.

    Parameters:
        access_token (str): The access token to use for authentication.
        user (User): The user object to associate the entitlements with.

    Returns:
        tuple[dict[str, Game], dict[str, str]]: A tuple containing a dictionary of entitlements
        with concept IDs as keys and Game objects as values, and a dictionary of title IDs
        with title IDs as keys and concept IDs as values.
    """
    entitlements: dict[str, Game] = {}
    titleIds: dict[str, str] = {}
    offset = entitlements_offset
    while offset is not None:
        response = await make_psn_request(
            f"https://m.np.playstation.com/api/entitlement/v2/users/me/internal/entitlements?fields=titleMeta%2CgameMeta%2CconceptMeta%2CrewardMeta%2CrewardMeta.retentionPolicy%2CrewardMeta.rewardMembershipType&gameMetaPackageType=PSGD%2CPS4GD&limit=100&offset={offset}&sortBy=ACTIVE_DATE",
            access_token,
        )
        entitlementsResult = EntitlementsResult(**response)
        for game in entitlementsResult.entitlements:
            if (
                game.conceptMeta
                and game.conceptMeta.name
                and game.conceptMeta.conceptId
            ):
                if game.conceptMeta.conceptId not in entitlements.keys():
                    ownership = "own"
                    if game.rewardMeta.retentionPolicy == 4:
                        ownership = "psp"
                    elif game.rewardMeta.retentionPolicy == 5:
                        ownership = "pgc"

                    entitlements[game.conceptMeta.conceptId] = Game(
                        owner=user,
                        title=game.titleMeta.name,
                        psn_id=game.conceptMeta.conceptId,
                        ps4=game.entitlementAttributes[0].platformId == "ps4",
                        ps5=game.entitlementAttributes[0].platformId == "ps5",
                        ownership=ownership,
                        active=game.activeFlag,
                        active_date=game.activeDate,
                    )
                else:
                    if game.entitlementAttributes[0].platformId == "ps4":
                        entitlements[game.conceptMeta.conceptId].ps4 = True
                    elif game.entitlementAttributes[0].platformId == "ps5":
                        entitlements[game.conceptMeta.conceptId].ps5 = True

                titleIds[game.titleMeta.titleId] = game.conceptMeta.conceptId

        if offset + 100 >= entitlementsResult.totalResults:
            offset = None
        else:
            offset += 100

    return entitlements, titleIds, entitlementsResult.totalResults


@dramatiq.actor
async def load_trophy(titleId: int, user_id: int) -> None:
    f = Fernet(
        os.getenv("FERNET_KEY").encode()  # type: ignore
    )
    try:
        user = await User.objects.select_related("account").aget(pk=user_id)
        access_token = f.decrypt(user.account.access_token).decode()

        response = await make_psn_request(
            f"https://m.np.playstation.com/api/trophy/v1/users/me/titles/trophyTitles?npTitleIds={titleId}&includeNotEarnedTrophyIds=true",
            access_token,
        )
        trophy = TitleResult(**response).titles[0].trophyTitles[0]

        game = await TitleId.objects.select_related("game").aget(
            owner=user, title_id=titleId
        )
        g = game.game.psn_id

        try:
            gameTrophy = await GameTrophy.objects.aget(psn_id=g)
        except GameTrophy.DoesNotExist:
            gameTrophy = None
            if trophy.npServiceName == "trophy2":
                trophy_ps5 = trophy.npCommunicationId
                trophy_ps4 = None
            else:
                trophy_ps4 = trophy.npCommunicationId
                trophy_ps5 = None
            gameTrophy = GameTrophy(
                psn_id=g,
                name=trophy.trophyTitleName,
                trophy_id=trophy_ps5,
                trophy_id_ps4=trophy_ps4,
            )
            await gameTrophy.asave()

        if trophy.earnedTrophies == trophy.definedTrophies:
            game.game.status = "com"
            await game.game.asave()
        elif (
            gameTrophy.beaten_id
            and gameTrophy.beaten_id not in trophy.notEarnedTrophyIds
        ):
            game.game.status = "bea"
            await game.game.asave()

    except Exception as e:
        print(e)


@dramatiq.actor
async def load_games(user_id: int) -> None:
    """
    Load games associated with a user's PlayStation Network account.

    This task retrieves a user's game entitlements and trophy progress from the
    PlayStation Network using the PSNAWP API. It updates the user's game library
    in the database, including game ownership, platform availability (PS4/PS5),
    game status (completed, beaten, or unfinished), and playtime statistics.

    Parameters:
    - user_id (int): The primary key of the user whose games are to be loaded.

    Raises:
    - PSNAWPAuthenticationError: If there is an issue authenticating with the PSNAWP API.
    """
    user = await User.objects.select_related("account").aget(pk=user_id)
    try:
        f = Fernet(
            os.getenv("FERNET_KEY").encode()  # type: ignore
        )
        npsso = f.decrypt(user.account.psn_token).decode()
        psnawp = PSNAWP(npsso)
        client = psnawp.me()
        client.online_id
        if client.authenticator.token_response:
            access_token = client.authenticator.token_response["access_token"]
            (
                (entitlements, titleIds, totalEntitlements),
                gameStats,
            ) = await asyncio.gather(
                get_entitlements(
                    access_token=access_token,
                    user=user,
                    entitlements_offset=user.account.entitlements_offset,
                ),
                get_title_stats(
                    access_token=access_token, last_played=user.account.last_played
                ),
            )
            titleIdsStats: list[str] = []
            for game in gameStats:
                if game.titleId and game.titleId in titleIds.keys():
                    titleIdsStats.append(game.titleId)

            trophies = await fetch_with_rate_limit(titleIdsStats[:200], access_token)

            if len(titleIdsStats) > 200:
                user.account.access_token = f.encrypt(access_token.encode())
                delay = 900000
                for titleId in titleIdsStats[200:]:
                    load_trophy.send_with_options(args=(titleId, user.pk), delay=delay)
                    delay += 5000

            trophiesData: dict[str, TrophyTitles] = {}
            for trophy in trophies:
                if (
                    not isinstance(trophy, BaseException)
                    and len(trophy.titles[0].trophyTitles) > 0
                ):
                    trophiesData[trophy.titles[0].npTitleId] = trophy.titles[
                        0
                    ].trophyTitles[0]

            last_played: datetime | None = None
            if len(gameStats) > 0:
                if gameStats[0].lastPlayedDateTime:
                    last_played = gameStats[0].lastPlayedDateTime

            for game in gameStats:
                saved_game = None
                if game.titleId and game.titleId not in titleIds.keys():
                    try:
                        title_game = await TitleId.objects.select_related("game").aget(
                            owner=user, title_id=game.titleId
                        )
                        saved_game = title_game.game
                        if game.titleId:
                            titleIds[game.titleId] = str(saved_game.psn_id)
                    except Exception as e:
                        print(f"{game.name}: {e}")
                if (
                    game.titleId
                    and game.titleId in titleIds.keys()
                    and (saved_game or (titleIds[game.titleId] in entitlements.keys()))
                ):
                    g = titleIds[game.titleId]

                    if (
                        saved_game
                        and game.lastPlayedDateTime
                        and saved_game.last_played == game.lastPlayedDateTime
                    ):
                        break

                    completed = False
                    beaten = False

                    try:
                        gameTrophy = await GameTrophy.objects.aget(psn_id=g)
                    except GameTrophy.DoesNotExist:
                        gameTrophy = None
                        if game.titleId in trophiesData.keys():
                            if trophiesData[game.titleId].npServiceName == "trophy2":
                                trophy_ps5 = trophiesData[
                                    game.titleId
                                ].npCommunicationId
                                trophy_ps4 = None
                            else:
                                trophy_ps4 = trophiesData[
                                    game.titleId
                                ].npCommunicationId
                                trophy_ps5 = None
                            gameTrophy = GameTrophy(
                                psn_id=g,
                                name=trophiesData[game.titleId].trophyTitleName,
                                trophy_id=trophy_ps5,
                                trophy_id_ps4=trophy_ps4,
                            )
                            await gameTrophy.asave()
                    except GameTrophy.MultipleObjectsReturned:
                        gameTrophy = None

                    if gameTrophy and game.titleId in trophiesData.keys():
                        if (
                            trophiesData[game.titleId].earnedTrophies
                            == trophiesData[game.titleId].definedTrophies
                        ):
                            completed = True
                        elif gameTrophy.beaten_id:
                            if (
                                gameTrophy.beaten_id
                                not in trophiesData[game.titleId].notEarnedTrophyIds
                            ):
                                beaten = True

                    if not saved_game:
                        if completed:
                            entitlements[g].status = "com"
                        elif beaten:
                            entitlements[g].status = "bea"
                        elif (
                            entitlements[g].status != "com"
                            and entitlements[g].status != "bea"
                        ):
                            entitlements[g].status = "unf"
                        entitlement_data = entitlements[g]
                        if game.firstPlayedDateTime and (
                            not entitlement_data.first_played
                            or (
                                entitlement_data.first_played > game.firstPlayedDateTime
                            )
                        ):
                            entitlements[g].first_played = game.firstPlayedDateTime
                        if game.lastPlayedDateTime and (
                            not entitlement_data.last_played
                            or entitlement_data.last_played < game.lastPlayedDateTime
                        ):
                            entitlements[g].last_played = game.lastPlayedDateTime
                        if game.playDuration:
                            if entitlement_data.playtime is not None:
                                entitlements[g].playtime += int(
                                    game.playDuration.total_seconds() / 60
                                )  # type: ignore
                            else:
                                entitlements[g].playtime = int(
                                    game.playDuration.total_seconds() / 60
                                )

                    elif (
                        game.lastPlayedDateTime
                        and game.lastPlayedDateTime != saved_game.last_played
                    ):
                        if (
                            not saved_game.last_played
                            or saved_game.last_played < game.lastPlayedDateTime
                        ):
                            saved_game.last_played = game.lastPlayedDateTime

                        if game.playDuration:
                            saved_game.playtime = int(
                                game.playDuration.total_seconds() / 60
                            )

                        if beaten and saved_game.status != "bea":
                            saved_game.status = "bea"
                        elif completed and saved_game.status != "com":
                            saved_game.status = "com"

                        await saved_game.asave()

        entitlements_list = list(entitlements.values())
        entitlements_list.reverse()
        await Game.objects.abulk_create(entitlements_list)

        title_objects = []
        for key, value in titleIds.items():
            if value in entitlements.keys():
                title_objects.append(
                    TitleId(title_id=key, game=entitlements[value], owner=user)
                )

        await TitleId.objects.abulk_create(title_objects)
        user.account.last_updated = timezone.now()
        user.account.entitlements_offset = totalEntitlements
        if last_played:
            user.account.last_played = last_played

    except PSNAWPAuthenticationError:
        user.account.token_is_valid = False

    finally:
        user.account.loading_data = False
        await user.account.asave()
