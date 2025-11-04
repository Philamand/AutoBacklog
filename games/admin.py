from django.contrib import admin
from import_export import resources
from import_export.fields import Field
from import_export.admin import ImportExportModelAdmin
from .models import Game, GameTrophy, TitleId, PlayStationTitle

admin.site.register(Game)

admin.site.register(TitleId)


@admin.register(GameTrophy)
class GameTrophyAdmin(admin.ModelAdmin):
    ordering = ["name"]
    list_filter = [("beaten_id", admin.EmptyFieldListFilter)]
    list_display = ["id", "name"]
    sortable_by = ["id", "name"]


class PlayStationTitleResource(resources.ModelResource):
    title_id_field = Field(attribute="title_id", column_name="titleId")
    concept_id_field = Field(attribute="concept_id", column_name="conceptId")
    name_field = Field(attribute="name", column_name="name")
    content_id_field = Field(attribute="content_id", column_name="contentId")
    region_field = Field(attribute="region", column_name="region")
    publisher_id_field = Field(attribute="publisher_id", column_name="publisherId")

    class Meta:
        model = PlayStationTitle
        fields = (
            "title_id_field",
            "concept_id_field",
            "name_field",
            "content_id_field",
            "region_field",
            "publisher_id_field",
        )
        import_id_fields = ("title_id_field",)


@admin.register(PlayStationTitle)
class PlayStationTitleAdmin(ImportExportModelAdmin):
    resource_class = PlayStationTitleResource
    list_display = (
        "title_id",
        "concept_id",
        "name",
        "content_id",
        "region",
        "publisher_id",
    )
