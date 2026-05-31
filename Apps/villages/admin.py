from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html, format_html_join

from .models import Infrastructure, TypeInfrastructure, Village


class InfrastructureInline(admin.TabularInline):
    model = Infrastructure
    extra = 0
    show_change_link = True
    fields = (
        "type_infrastructure",
        "nom",
        "etat",
        "capacite",
        "responsable",
        "contact_responsable",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(deleted__isnull=True)


@admin.register(Village)
class VillageAdmin(admin.ModelAdmin):
    list_display = (
        "nom",
        "chef_village",
        "nb_familles_display",
        "nb_habitants_display",
        "nb_infras_display",
        "infras_par_type_display",
        "date_creation",
    )
    list_display_links = ("nom",)
    search_fields = ("nom", "chef_village")
    list_filter = ("date_creation",)
    ordering = ("nom",)
    list_per_page = 30
    readonly_fields = (
        "id",
        "date_creation",
        "nb_familles_display",
        "nb_habitants_display",
        "nb_infras_display",
        "infras_par_type_display",
        "carte_preview",
    )
    inlines = [InfrastructureInline]

    fieldsets = (
        (
            "Informations generales",
            {
                "fields": (
                    "id",
                    ("nom", "chef_village"),
                    "description",
                )
            },
        ),
        (
            "Population",
            {
                "fields": (
                    "nb_familles_display",
                    "nb_habitants_display",
                )
            },
        ),
        (
            "Localisation GPS",
            {
                "fields": (
                    ("latitude", "longitude"),
                    "carte_preview",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Infrastructures",
            {
                "fields": (
                    "nb_infras_display",
                    "infras_par_type_display",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Meta",
            {
                "fields": ("date_creation",),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Familles")
    def nb_familles_display(self, obj):
        if obj is None:
            return "-"
        n = obj.nombre_familles
        if n == 0:
            return "-"
        url = f"/admin/families/family/?village__id__exact={obj.id}"
        return format_html('<a href="{}">{} famille(s)</a>', url, n)

    @admin.display(description="Habitants")
    def nb_habitants_display(self, obj):
        if obj is None:
            return "-"
        n = obj.nombre_habitants
        return f"{n} personne(s)" if n > 0 else "-"

    @admin.display(description="Infrastructures")
    def nb_infras_display(self, obj):
        if obj is None:
            return "-"
        n = obj.nombre_total_infrastructures
        if n == 0:
            return format_html(
                '<span style="color:var(--color-text-tertiary)">{}</span>',
                "Aucune",
            )
        return format_html(
            '<strong style="color:#0F6E56">{}</strong> infra(s)',
            n,
        )

    @admin.display(description="Detail infrastructures")
    def infras_par_type_display(self, obj):
        if obj is None:
            return "-"
        data = obj.get_infrastructures_by_type()
        if not data:
            return "-"
        return format_html_join(
            "",
            '<span style="display:inline-block;margin:2px 4px 2px 0;'
            'padding:2px 8px;border-radius:10px;font-size:11px;'
            'background:#E1F5EE;color:#0F6E56;">{} ({})</span>',
            ((label, count) for label, count in data.items()),
        )

    @admin.display(description="Carte")
    def carte_preview(self, obj):
        if obj and obj.latitude and obj.longitude:
            url = f"https://www.google.com/maps?q={obj.latitude},{obj.longitude}"
            return format_html(
                '<a href="{}" target="_blank" style="color:#185FA5;">Voir sur Google Maps</a>',
                url,
            )
        return format_html(
            '<span style="color:var(--color-text-tertiary)">{}</span>',
            "Coordonnees non renseignees",
        )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _nb_infras=Count(
                "infrastructures",
                filter=Q(infrastructures__deleted__isnull=True),
            )
        )

    actions = ["exporter_csv"]

    @admin.action(description="Exporter en CSV")
    def exporter_csv(self, request, queryset):
        import csv

        from django.http import HttpResponse

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="villages_olodio.csv"'
        response.write("\ufeff")

        writer = csv.writer(response)
        writer.writerow(
            [
                "ID",
                "Nom",
                "Chef de village",
                "Membres enregistres",
                "Nb familles",
                "Nb infrastructures",
                "Latitude",
                "Longitude",
                "Date creation",
            ]
        )
        for village in queryset:
            writer.writerow(
                [
                    str(village.id),
                    village.nom,
                    village.chef_village or "-",
                    village.nombre_habitants,
                    village.nombre_familles,
                    village.nombre_total_infrastructures,
                    village.latitude or "",
                    village.longitude or "",
                    village.date_creation.strftime("%d/%m/%Y"),
                ]
            )
        return response


@admin.register(TypeInfrastructure)
class TypeInfrastructureAdmin(admin.ModelAdmin):
    list_display = ("nom", "icone", "description")
    search_fields = ("nom",)
    ordering = ("nom",)
    fieldsets = (
        (
            "Type d'infrastructure",
            {
                "fields": ("nom", "icone", "description"),
            },
        ),
    )


@admin.register(Infrastructure)
class InfrastructureAdmin(admin.ModelAdmin):
    list_display = (
        "nom",
        "type_badge_display",
        "village",
        "etat_badge_display",
        "capacite",
        "responsable",
        "contact_responsable",
        "date_construction",
    )
    list_display_links = ("nom",)
    list_filter = (
        "type_infrastructure",
        "etat",
        "village",
        "date_construction",
    )
    search_fields = (
        "nom",
        "responsable",
        "village__nom",
    )
    ordering = ("village", "type_infrastructure", "nom")
    list_per_page = 40
    date_hierarchy = "date_construction"
    autocomplete_fields = ["village"]
    readonly_fields = (
        "id",
        "date_creation",
        "date_modification",
    )

    fieldsets = (
        (
            "Identification",
            {
                "fields": (
                    "id",
                    ("village", "type_infrastructure"),
                    "nom",
                    "description",
                )
            },
        ),
        (
            "Details",
            {
                "fields": (
                    ("etat", "capacite"),
                    "date_construction",
                )
            },
        ),
        (
            "Responsable",
            {
                "fields": (
                    ("responsable", "contact_responsable"),
                )
            },
        ),
        (
            "Meta",
            {
                "fields": (
                    "date_creation",
                    "date_modification",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    TYPE_COLORS = {
        "ecole": ("#EAF3DE", "#27500A"),
        "ecole_maternelle": ("#EAF3DE", "#27500A"),
        "lycee": ("#EAF3DE", "#27500A"),
        "universite": ("#EAF3DE", "#27500A"),
        "hopital": ("#FAECE7", "#712B13"),
        "dispensaire": ("#FAECE7", "#712B13"),
        "centre_sante": ("#FAECE7", "#712B13"),
        "marche": ("#FAEEDA", "#633806"),
        "mairie": ("#EEEDFE", "#26215C"),
        "poste_police": ("#EEEDFE", "#26215C"),
        "place_publique": ("#E1F5EE", "#04342C"),
        "centre_communautaire": ("#E1F5EE", "#04342C"),
        "puit": ("#E6F1FB", "#042C53"),
        "forage": ("#E6F1FB", "#042C53"),
        "electricite": ("#FAEEDA", "#412402"),
        "telephone": ("#FAEEDA", "#412402"),
        "internet": ("#FAEEDA", "#412402"),
        "autre": ("#F1EFE8", "#2C2C2A"),
    }

    ETAT_COLORS = {
        "bon": ("#EAF3DE", "#27500A", "Bon etat"),
        "moyen": ("#FAEEDA", "#633806", "Etat moyen"),
        "mauvais": ("#FAECE7", "#712B13", "Mauvais etat"),
        "en_construction": ("#E6F1FB", "#042C53", "En construction"),
        "abandonne": ("#F1EFE8", "#444441", "Abandonne"),
    }

    @admin.display(description="Type")
    def type_badge_display(self, obj):
        bg, color = self.TYPE_COLORS.get(
            obj.type_infrastructure,
            ("#F1EFE8", "#2C2C2A"),
        )
        return format_html(
            '<span style="display:inline-block;padding:2px 9px;'
            'border-radius:10px;font-size:11px;font-weight:500;'
            'background:{};color:{};">{}</span>',
            bg,
            color,
            obj.get_type_infrastructure_display(),
        )

    @admin.display(description="Etat")
    def etat_badge_display(self, obj):
        bg, color, label = self.ETAT_COLORS.get(
            obj.etat,
            ("#F1EFE8", "#444441", obj.etat),
        )
        return format_html(
            '<span style="display:inline-block;padding:2px 9px;'
            'border-radius:10px;font-size:11px;font-weight:500;'
            'background:{};color:{};">{}</span>',
            bg,
            color,
            label,
        )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(
            deleted__isnull=True
        ).select_related("village")

    actions = ["marquer_bon_etat", "marquer_mauvais_etat", "exporter_csv"]

    @admin.action(description="Marquer en bon etat")
    def marquer_bon_etat(self, request, queryset):
        n = queryset.update(etat="bon")
        self.message_user(request, f"{n} infrastructure(s) marquee(s) en bon etat.")

    @admin.action(description="Marquer en mauvais etat")
    def marquer_mauvais_etat(self, request, queryset):
        n = queryset.update(etat="mauvais")
        self.message_user(
            request,
            f"{n} infrastructure(s) marquee(s) en mauvais etat.",
            level="warning",
        )

    @admin.action(description="Exporter en CSV")
    def exporter_csv(self, request, queryset):
        import csv

        from django.http import HttpResponse

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            'attachment; filename="infrastructures_olodio.csv"'
        )
        response.write("\ufeff")

        writer = csv.writer(response)
        writer.writerow(
            [
                "ID",
                "Village",
                "Type",
                "Nom",
                "Etat",
                "Capacite",
                "Responsable",
                "Contact",
                "Date construction",
                "Date creation",
            ]
        )
        for infrastructure in queryset.select_related("village"):
            writer.writerow(
                [
                    str(infrastructure.id),
                    infrastructure.village.nom,
                    infrastructure.get_type_infrastructure_display(),
                    infrastructure.nom,
                    infrastructure.get_etat_display(),
                    infrastructure.capacite or "-",
                    infrastructure.responsable or "-",
                    infrastructure.contact_responsable or "-",
                    infrastructure.date_construction.strftime("%d/%m/%Y")
                    if infrastructure.date_construction
                    else "-",
                    infrastructure.date_creation.strftime("%d/%m/%Y"),
                ]
            )
        return response
