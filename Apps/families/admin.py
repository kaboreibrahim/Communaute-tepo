import csv

from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html

from .models import Family


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = (
        "nom_famille",
        "village",
        "chef_display",
        "nb_membres_display",
        "nb_vivants_display",
        "nb_diaspora_display",
        "date_creation",
        "date_maj",
    )
    list_display_links = ("nom_famille",)
    list_filter = ("village", "date_creation", "date_maj")
    search_fields = ("nom_famille", "village__nom", "description")
    ordering = ("village__nom", "nom_famille")
    list_per_page = 30
    date_hierarchy = "date_creation"
    autocomplete_fields = ["village"]
    readonly_fields = (
        "id",
        "chef_display",
        "nb_membres_display",
        "nb_vivants_display",
        "nb_hommes_display",
        "nb_femmes_display",
        "nb_diaspora_display",
        "date_creation",
        "date_maj",
    )
    actions = ["exporter_csv"]

    fieldsets = (
        (
            "Identification",
            {
                "fields": (
                    "id",
                    ("nom_famille", "village"),
                    "description",
                )
            },
        ),
        (
            "Composition",
            {
                "fields": (
                    "chef_display",
                    ("nb_membres_display", "nb_vivants_display"),
                    ("nb_hommes_display", "nb_femmes_display"),
                    "nb_diaspora_display",
                )
            },
        ),
        (
            "Meta",
            {
                "fields": ("date_creation", "date_maj"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("village")

    def _get_membres_manager(self, obj):
        return getattr(obj, "membres", None)

    def _relation_has_fields(self, manager, *field_names):
        if manager is None or not hasattr(manager, "model"):
            return False

        for field_name in field_names:
            try:
                manager.model._meta.get_field(field_name)
            except Exception:
                return False
        return True

    def _build_membres_queryset(self, obj):
        manager = self._get_membres_manager(obj)
        if manager is None:
            return None

        queryset = manager.all()
        if self._relation_has_fields(manager, "deleted"):
            queryset = queryset.filter(deleted__isnull=True)
        return queryset

    def _count_members(self, obj, **filters):
        queryset = self._build_membres_queryset(obj)
        if queryset is None:
            return 0

        try:
            return queryset.filter(**filters).count()
        except Exception:
            return 0

    def _muted(self, text):
        return format_html(
            '<span style="color:var(--color-text-tertiary)">{}</span>',
            text,
        )

    def _get_chef(self, obj):
        queryset = self._build_membres_queryset(obj)
        if queryset is None:
            return None

        manager = self._get_membres_manager(obj)
        if self._relation_has_fields(manager, "est_chef_famille"):
            return queryset.filter(
                est_chef_famille=True,
            ).order_by("date_creation", "nom", "prenom").first()
        return queryset.first()

    @admin.display(description="Chef de famille")
    def chef_display(self, obj):
        queryset = self._build_membres_queryset(obj)
        if queryset is None:
            return self._muted("Non disponible")

        chef = self._get_chef(obj)
        if chef is None:
            return self._muted("Non renseigne")
        return str(chef)

    @admin.display(description="Membres")
    def nb_membres_display(self, obj):
        total = self._count_members(obj)
        if total == 0:
            return self._muted("0")
        return format_html(
            '<strong style="color:#0F6E56;">{}</strong> membre(s)',
            total,
        )

    @admin.display(description="Vivants")
    def nb_vivants_display(self, obj):
        total = self._count_members(obj, est_vivant=True)
        return total if total > 0 else self._muted("0")

    @admin.display(description="Hommes")
    def nb_hommes_display(self, obj):
        total = self._count_members(obj, genre="M")
        return total if total > 0 else self._muted("0")

    @admin.display(description="Femmes")
    def nb_femmes_display(self, obj):
        total = self._count_members(obj, genre="F")
        return total if total > 0 else self._muted("0")

    @admin.display(description="Diaspora")
    def nb_diaspora_display(self, obj):
        total = self._count_members(obj, type_residence="diaspora")
        return total if total > 0 else self._muted("0")

    @admin.action(description="Exporter en CSV")
    def exporter_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="familles_olodio.csv"'
        response.write("\ufeff")

        writer = csv.writer(response)
        writer.writerow(
            [
                "ID",
                "Nom de famille",
                "Village",
                "Chef de famille",
                "Nb membres",
                "Nb vivants",
                "Nb diaspora",
                "Description",
                "Date creation",
                "Date mise a jour",
            ]
        )

        for famille in queryset.select_related("village"):
            chef = self._get_chef(famille)
            writer.writerow(
                [
                    str(famille.id),
                    famille.nom_famille,
                    famille.village.nom,
                    str(chef) if chef else "",
                    self._count_members(famille),
                    self._count_members(famille, est_vivant=True),
                    self._count_members(famille, type_residence="diaspora"),
                    famille.description or "",
                    famille.date_creation.strftime("%d/%m/%Y %H:%M"),
                    famille.date_maj.strftime("%d/%m/%Y %H:%M"),
                ]
            )

        return response
