from django.contrib import admin
from .models import Game, GameTrophy, TitleId

admin.site.register(Game)

admin.site.register(TitleId)


@admin.register(GameTrophy)
class GameTrophyAdmin(admin.ModelAdmin):
    ordering = ["name"]
    list_filter = [("beaten_id", admin.EmptyFieldListFilter)]
    list_display = ["id", "name"]
    sortable_by = ["id", "name"]
