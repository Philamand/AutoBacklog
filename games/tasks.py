import json
import dramatiq
import httpx
import asyncio
import os
from cryptography.fernet import Fernet
from asgiref.sync import sync_to_async
from asyncio import Semaphore
from pydantic import BaseModel, ValidationError
from datetime import datetime, timedelta
from psnawp_api import PSNAWP
from psnawp_api.models.search import SearchDomain
from psnawp_api.core.psnawp_exceptions import PSNAWPAuthenticationError
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Game, GameTrophy, TitleId, PlayStationTitle
from accounts.models import EntitlementsUpload, EntitlementsDownload
from psn_account.models import PsnAccount


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


class GameEntitlements(BaseModel):
    """Represents a list of game entitlement entries."""

    entitlements: list[GameEntitlement]


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
    service: str | None = None
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


async def get_title_stats(
    access_token: str, account_id: str, last_played: datetime | None = None
) -> list[TitleStats]:
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
            f"https://m.np.playstation.com/api/gamelist/v2/users/{account_id}/titles?limit=100&offset={str(offset)}",
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
async def load_entitlements(entitlement_id: int) -> None:
    entitlement_upload = await EntitlementsUpload.objects.prefetch_related(
        "user__account"
    ).aget(pk=entitlement_id)

    if not entitlement_upload.user.account.account_id:
        return

    create_games = {}
    update_games = {}

    try:
        game_entitlements = GameEntitlements(entitlements=entitlement_upload.data)
    except ValidationError:
        return

    for entitlement in game_entitlements.entitlements:
        if entitlement.conceptMeta.conceptId:
            if (
                entitlement.conceptMeta.conceptId not in create_games.keys()
                and entitlement.conceptMeta.conceptId not in update_games.keys()
            ):
                try:
                    game = await Game.objects.aget(
                        owner=entitlement_upload.user,
                        psn_id=entitlement.conceptMeta.conceptId,
                    )
                    update_games[entitlement.conceptMeta.conceptId] = game
                except Game.DoesNotExist:
                    playstation_title = (
                        await PlayStationTitle.objects.filter(
                            concept_id=entitlement.conceptMeta.conceptId
                        )
                        .exclude(concept_id=None)
                        .order_by("region")
                        .afirst()
                    )
                    if playstation_title:
                        game = Game(
                            owner=entitlement_upload.user,
                            title=playstation_title.name,
                            psn_id=entitlement.conceptMeta.conceptId,
                        )
                        create_games[entitlement.conceptMeta.conceptId] = game

            if entitlement.conceptMeta.conceptId in create_games.keys():
                create_games[
                    entitlement.conceptMeta.conceptId
                ].active = entitlement.activeFlag
                create_games[
                    entitlement.conceptMeta.conceptId
                ].active_date = entitlement.activeDate
                if entitlement.entitlementAttributes[0].platformId == "ps4":
                    create_games[entitlement.conceptMeta.conceptId].ps4 = True
                else:
                    create_games[entitlement.conceptMeta.conceptId].ps5 = True
                if entitlement.rewardMeta.retentionPolicy == 4:
                    create_games[entitlement.conceptMeta.conceptId].ownership = "psp"
                elif entitlement.rewardMeta.retentionPolicy == 5:
                    create_games[entitlement.conceptMeta.conceptId].ownership = "pgc"
            elif entitlement.conceptMeta.conceptId in update_games.keys():
                update_games[
                    entitlement.conceptMeta.conceptId
                ].active = entitlement.activeFlag
                update_games[
                    entitlement.conceptMeta.conceptId
                ].active_date = entitlement.activeDate
                if entitlement.entitlementAttributes[0].platformId == "ps4":
                    update_games[entitlement.conceptMeta.conceptId].ps4 = True
                else:
                    update_games[entitlement.conceptMeta.conceptId].ps5 = True
                if entitlement.rewardMeta.retentionPolicy == 4:
                    update_games[entitlement.conceptMeta.conceptId].ownership = "psp"
                elif entitlement.rewardMeta.retentionPolicy == 5:
                    update_games[entitlement.conceptMeta.conceptId].ownership = "pgc"

    async for user_game in Game.objects.filter(owner=entitlement_upload.user):
        if (
            user_game.psn_id
            and user_game.psn_id not in update_games.keys()
            and user_game.psn_id not in create_games.keys()
        ):
            user_game.ownership = "phy"
            update_games[user_game.psn_id] = user_game

    if update_games:
        await Game.objects.abulk_update(
            list(update_games.values()),
            [
                "ps4",
                "ps5",
                "ownership",
                "active",
                "active_date",
            ],
        )
    if create_games:
        await Game.objects.abulk_create(list(create_games.values()))


@dramatiq.actor
async def download_entitlements(download_id: int) -> None:
    try:
        entitlement_download = await EntitlementsDownload.objects.prefetch_related(
            "user"
        ).aget(pk=download_id)
    except EntitlementsDownload.DoesNotExist:
        return

    f = Fernet(
        os.getenv("FERNET_KEY").encode()  # type: ignore
    )

    npsso = f.decrypt(entitlement_download.npsso).decode()

    try:
        psnawp = PSNAWP(npsso)
        client = psnawp.me()

        game_entitlements = []

        for game_entitlement in client.game_entitlements():
            game_entitlements.append(game_entitlement)

        entitlement_upload = EntitlementsUpload(
            user=entitlement_download.user, data=game_entitlements
        )

        await entitlement_upload.asave()

        await sync_to_async(load_entitlements.send)(entitlement_upload.pk)

    except Exception as e:
        print(e)

    finally:
        await entitlement_download.adelete()


@dramatiq.actor
async def load_trophy(titleId: str, conceptId: int, user_id: int) -> None:
    psn_account: PsnAccount | None = None

    while not psn_account:
        psn_account = await (
            PsnAccount.objects.filter(ready__lt=timezone.now())
            .exclude(npsso_is_valid=False)
            .exclude(available=False)
            .afirst()
        )
        if not psn_account or not psn_account.npsso:
            await asyncio.sleep(10)

    psn_account.available = False
    if psn_account.ready < timezone.now():
        psn_account.ready = timezone.now()
    await psn_account.asave()
    try:
        user = await User.objects.select_related("account").aget(pk=user_id)
        psnawp = PSNAWP(psn_account.npsso)  # type: ignore
        client = psnawp.me()
        client.online_id
        if client.authenticator.token_response:
            access_token = client.authenticator.token_response["access_token"]

            response = await make_psn_request(
                f"https://m.np.playstation.com/api/trophy/v1/users/{user.account.account_id}/titles/trophyTitles?npTitleIds={titleId}&includeNotEarnedTrophyIds=true",
                access_token,
            )

            psn_account.ready += timedelta(seconds=3)

            trophy = TitleResult(**response).titles[0].trophyTitles[0]

            game = await Game.objects.aget(owner=user, psn_id=conceptId)

            try:
                gameTrophy = await GameTrophy.objects.aget(psn_id=conceptId)
            except GameTrophy.DoesNotExist:
                gameTrophy = None
                if trophy.npServiceName == "trophy2":
                    trophy_ps5 = trophy.npCommunicationId
                    trophy_ps4 = None
                else:
                    trophy_ps4 = trophy.npCommunicationId
                    trophy_ps5 = None
                gameTrophy = GameTrophy(
                    psn_id=conceptId,
                    name=trophy.trophyTitleName,
                    trophy_id=trophy_ps5,
                    trophy_id_ps4=trophy_ps4,
                )
                await gameTrophy.asave()

            if trophy.earnedTrophies == trophy.definedTrophies:
                game.status = "com"
                await game.asave()
            elif (
                gameTrophy.beaten_id
                and gameTrophy.beaten_id not in trophy.notEarnedTrophyIds
            ):
                game.status = "bea"
                await game.asave()

    except Exception as e:
        print(e)
    finally:
        psn_account.available = True
        await psn_account.asave()


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
    if not user.account.account_id:
        return

    psn_account: PsnAccount | None = None

    while not psn_account:
        psn_account = await (
            PsnAccount.objects.filter(ready__lt=timezone.now())
            .exclude(npsso_is_valid=False)
            .exclude(available=False)
            .afirst()
        )
        if not psn_account or not psn_account.npsso:
            await asyncio.sleep(60)

    psn_account.available = False
    if psn_account.ready < timezone.now():
        psn_account.ready = timezone.now()
    await psn_account.asave()

    try:
        psnawp = PSNAWP(psn_account.npsso)  # type: ignore
        client = psnawp.me()
        client.online_id
        update_games = {}
        create_games = {}

        if client.authenticator.token_response:
            access_token = client.authenticator.token_response["access_token"]
            game_stats = await get_title_stats(
                access_token=access_token, account_id=user.account.account_id
            )

            psn_account.ready += timedelta(seconds=(len(game_stats) / 100 + 1) * 3)

            game_count = 0

            for game_stat in game_stats:
                if game_stat.titleId:
                    playstation_title = await (
                        PlayStationTitle.objects.filter(title_id=game_stat.titleId)
                        .exclude(concept_id=None)
                        .order_by("region")
                        .afirst()
                    )
                    if playstation_title and playstation_title.concept_id:
                        print(game_stat.name, game_stat.service)
                        try:
                            game = await Game.objects.aget(
                                owner=user, psn_id=playstation_title.concept_id
                            )
                            if game.psn_id in update_games.keys():
                                update_games[game.psn_id].playtime += int(
                                    game_stat.playDuration.total_seconds() / 60  # type: ignore
                                )
                                if game_stat.service == "ps_plus":
                                    update_games[game.psn_id].ownership = "psp"
                            else:
                                game.playtime = int(
                                    game_stat.playDuration.total_seconds() / 60  # type: ignore
                                )
                                if not game.first_played or (
                                    game_stat.firstPlayedDateTime
                                    and game_stat.firstPlayedDateTime
                                    > game.first_played
                                ):
                                    game.first_played = game_stat.firstPlayedDateTime
                                if not game.last_played or (
                                    game_stat.lastPlayedDateTime
                                    and game_stat.lastPlayedDateTime > game.last_played
                                ):
                                    game.last_played = game_stat.lastPlayedDateTime
                                if game_stat.service == "ps_plus":
                                    game.ownership = "psp"
                                update_games[game.psn_id] = game
                        except Game.DoesNotExist:
                            service = "own"
                            if game_stat.service == "ps_plus":
                                service = "psp"
                            if playstation_title.concept_id in create_games.keys():
                                create_games[
                                    playstation_title.concept_id
                                ].playtime += int(
                                    game_stat.playDuration.total_seconds() / 60  # type: ignore
                                )
                                if (
                                    not create_games[
                                        playstation_title.concept_id
                                    ].last_played
                                    or game_stat.firstPlayedDateTime
                                    < create_games[
                                        playstation_title.concept_id
                                    ].first_played
                                ):
                                    create_games[
                                        playstation_title.concept_id
                                    ].first_played = game_stat.firstPlayedDateTime
                                if (
                                    not create_games[
                                        playstation_title.concept_id
                                    ].last_played
                                    or game_stat.lastPlayedDateTime
                                    > create_games[
                                        playstation_title.concept_id
                                    ].last_played
                                ):
                                    create_games[
                                        playstation_title.concept_id
                                    ].last_played = game_stat.lastPlayedDateTime
                                if "CUSA" in game_stat.titleId:
                                    create_games[
                                        playstation_title.concept_id
                                    ].ps4 = True
                                else:
                                    create_games[
                                        playstation_title.concept_id
                                    ].ps5 = True
                            else:
                                create_games[playstation_title.concept_id] = Game(
                                    owner=user,
                                    title=playstation_title.name,
                                    psn_id=playstation_title.concept_id,
                                    ps4="CUSA" in game_stat.titleId,
                                    ps5="PPSA" in game_stat.titleId,
                                    status="unf",
                                    ownership=service,
                                    first_played=game_stat.firstPlayedDateTime,
                                    last_played=game_stat.lastPlayedDateTime,
                                    playtime=int(
                                        game_stat.playDuration.total_seconds() / 60  # type: ignore
                                    ),
                                )
                        game_count += 1
                        if game_count < 200 and (
                            not user.account.last_played
                            or user.account.last_played < game_stat.lastPlayedDateTime
                        ):
                            try:
                                response = await make_psn_request(
                                    f"https://m.np.playstation.com/api/trophy/v1/users/{user.account.account_id}/titles/trophyTitles?npTitleIds={game_stat.titleId}&includeNotEarnedTrophyIds=true",
                                    access_token,
                                )
                                psn_account.ready += timedelta(seconds=3)
                                trophy = (
                                    TitleResult(**response).titles[0].trophyTitles[0]
                                )

                                try:
                                    gameTrophy = await GameTrophy.objects.aget(
                                        psn_id=playstation_title.concept_id
                                    )
                                except GameTrophy.DoesNotExist:
                                    gameTrophy = None
                                    if trophy.npServiceName == "trophy2":
                                        trophy_ps5 = trophy.npCommunicationId
                                        trophy_ps4 = None
                                    else:
                                        trophy_ps4 = trophy.npCommunicationId
                                        trophy_ps5 = None
                                    gameTrophy = GameTrophy(
                                        psn_id=playstation_title.concept_id,
                                        name=trophy.trophyTitleName,
                                        trophy_id=trophy_ps5,
                                        trophy_id_ps4=trophy_ps4,
                                    )
                                    await gameTrophy.asave()
                                if trophy.earnedTrophies == trophy.definedTrophies:
                                    if (
                                        playstation_title.concept_id
                                        in create_games.keys()
                                    ):
                                        create_games[
                                            playstation_title.concept_id
                                        ].status = "com"
                                    elif (
                                        playstation_title.concept_id
                                        in update_games.keys()
                                    ):
                                        update_games[
                                            playstation_title.concept_id
                                        ].status = "com"
                                elif (
                                    gameTrophy.beaten_id
                                    and gameTrophy.beaten_id
                                    not in trophy.notEarnedTrophyIds
                                ):
                                    if (
                                        playstation_title.concept_id
                                        in create_games.keys()
                                        and create_games[
                                            playstation_title.concept_id
                                        ].status
                                        != "com"
                                    ):
                                        create_games[
                                            playstation_title.concept_id
                                        ].status = "bea"
                                    elif (
                                        playstation_title.concept_id
                                        in update_games.keys()
                                        and update_games[
                                            playstation_title.concept_id
                                        ].status
                                        != "com"
                                    ):
                                        update_games[
                                            playstation_title.concept_id
                                        ].status = "bea"

                            except IndexError:
                                pass

                        elif (
                            not user.account.last_played
                            or user.account.last_played < game_stat.lastPlayedDateTime
                        ):
                            await sync_to_async(load_trophy.send_with_options)(
                                args=(
                                    game_stat.titleId,
                                    playstation_title.concept_id,
                                    user.pk,
                                ),
                                delay=((game_count - 199) * 5 + 900) * 1000,
                            )

        if update_games:
            await Game.objects.abulk_update(
                list(update_games.values()),
                [
                    "ps4",
                    "ps5",
                    "status",
                    "ownership",
                    "first_played",
                    "last_played",
                    "playtime",
                ],
            )
        if create_games:
            await Game.objects.abulk_create(list(create_games.values()))

    except PSNAWPAuthenticationError:
        psn_account.npsso_is_valid = False

    finally:
        psn_account.available = True
        await psn_account.asave()
        user.account.loading_data = False
        await user.account.asave()


@dramatiq.actor
async def get_account_id(user_id: int, playstation_username: str) -> None:
    user = await User.objects.select_related("account").aget(pk=user_id)

    psn_account: PsnAccount | None = None

    while not psn_account:
        psn_account = await (
            PsnAccount.objects.filter(ready__lt=timezone.now())
            .exclude(npsso_is_valid=False)
            .exclude(available=False)
            .afirst()
        )
        if not psn_account or not psn_account.npsso:
            await asyncio.sleep(10)

    psn_account.available = False
    if psn_account.ready < timezone.now():
        psn_account.ready = timezone.now()
    await psn_account.asave()

    try:
        psnawp = PSNAWP(psn_account.npsso)  # type: ignore

        results = psnawp.search(
            search_query=playstation_username, search_domain=SearchDomain.USERS
        )

        for result in results:
            if result["result"]["displayName"] == playstation_username:
                user.account.playstation_username = playstation_username
                user.account.account_id = result["result"]["accountId"]
                await user.account.asave()
                await sync_to_async(load_games.send)(user.pk)
            break

    except PSNAWPAuthenticationError:
        psn_account.npsso_is_valid = False

    finally:
        psn_account.available = True
        await psn_account.asave()
