import csv

from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html

from .models import Person


class VillageListFilter(admin.SimpleListFilter):
    title = "village"
    parameter_name = "village"

    def lookups(self, request, model_admin):
        villages = (
            model_admin.get_queryset(request)
            .values_list("famille__village_id", "famille__village__nom")
            .distinct()
            .order_by("famille__village__nom")
        )
        return [(str(village_id), nom) for village_id, nom in villages if village_id]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(famille__village_id=self.value())
        return queryset


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "nom_complet_display",
        "famille_display",
        "village_display",
        "genre_badge_display",
        "age_display",
        "situation_badge_display",
        "residence_badge_display",
        "est_vivant_badge_display",
    )
    list_display_links = ("nom_complet_display",)
    list_filter = (
        VillageListFilter,
        "famille",
        "genre",
        "est_vivant",
        "type_residence",
        "situation_matrimoniale",
        "date_creation",
    )
    search_fields = (
        "code",
        "nom",
        "prenom",
        "surnom",
        "telephone",
        "email",
        "numero_cni",
        "profession",
        "famille__nom_famille",
        "famille__village__nom",
        "pere__nom",
        "pere__prenom",
        "pere_nom_libre",
        "mere__nom",
        "mere__prenom",
        "mere_nom_libre",
        "conjoint__nom",
        "conjoint__prenom",
        "conjoint_nom_libre",
    )
    ordering = ("nom", "prenom")
    list_per_page = 30
    date_hierarchy = "date_creation"
    autocomplete_fields = ("famille", "pere", "mere", "conjoint")
    readonly_fields = (
        "id",
        "code",
        "nom_complet_display",
        "photo_preview",
        "age_display",
        "famille_display",
        "village_display",
        "parents_display",
        "conjoint_display",
        "generation_display",
        "a_profil_diaspora_display",
        "date_creation",
        "date_maj",
    )
    actions = ("exporter_csv",)
    empty_value_display = "-"

    fieldsets = (
        (
            "Identification",
            {
                "fields": (
                    ("id", "code"),
                    "nom_complet_display",
                    ("nom", "prenom", "surnom"),
                    ("genre", "famille"),
                    "photo",
                    "photo_preview",
                )
            },
        ),
        (
            "Etat civil",
            {
                "fields": (
                    ("date_naissance", "age_display"),
                    "lieu_naissance",
                    ("nationalite", "numero_cni"),
                    "profession",
                    ("situation_matrimoniale", "est_vivant"),
                    "date_deces",
                )
            },
        ),
        (
            "Contact et residence",
            {
                "fields": (
                    ("telephone", "email"),
                    ("type_residence", "lieu_residence"),
                    "a_profil_diaspora_display",
                )
            },
        ),
        (
            "Liens familiaux",
            {
                "fields": (
                    ("famille_display", "village_display"),
                    ("pere", "mere"),
                    ("pere_nom_libre", "mere_nom_libre"),
                    ("conjoint", "conjoint_nom_libre"),
                    "parents_display",
                    "conjoint_display",
                    ("generation_display", "est_chef_famille"),
                    "notes",
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

    GENRE_COLORS = {
        "M": ("#E6F1FB", "#042C53", "Masculin"),
        "F": ("#FAECE7", "#712B13", "Feminin"),
    }

    SITUATION_COLORS = {
        "celibataire": ("#F1EFE8", "#2C2C2A"),
        "marie": ("#E1F5EE", "#0F6E56"),
        "divorce": ("#FAEEDA", "#633806"),
        "veuf": ("#EEEDFE", "#26215C"),
    }

    RESIDENCE_COLORS = {
        "village": ("#EAF3DE", "#27500A"),
        "ci": ("#E6F1FB", "#042C53"),
        "diaspora": ("#EEEDFE", "#26215C"),
        "inconnu": ("#F1EFE8", "#444441"),
    }

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(deleted__isnull=True)
            .select_related("famille__village", "pere", "mere", "conjoint")
        )

    def _muted(self, text):
        return format_html(
            '<span style="color:var(--color-text-tertiary)">{}</span>',
            text,
        )

    def _badge(self, label, bg, color):
        return format_html(
            '<span style="display:inline-block;padding:2px 9px;'
            'border-radius:10px;font-size:11px;font-weight:500;'
            'background:{};color:{};">{}</span>',
            bg,
            color,
            label,
        )

    def save_model(self, request, obj, form, change):
        obj.pere_nom_libre = (obj.pere_nom_libre or "").strip()
        obj.mere_nom_libre = (obj.mere_nom_libre or "").strip()
        obj.conjoint_nom_libre = (obj.conjoint_nom_libre or "").strip()

        if obj.pere_nom_libre:
            obj.pere = None
        if obj.mere_nom_libre:
            obj.mere = None
        if obj.conjoint_nom_libre:
            obj.conjoint = None

        super().save_model(request, obj, form, change)

    @admin.display(description="Nom complet", ordering="prenom")
    def nom_complet_display(self, obj):
        if not obj:
            return self._muted("Non renseigne")
        if obj.surnom:
            return f"{obj.prenom} « {obj.surnom} » {obj.nom}"
        return obj.nom_complet

    @admin.display(description="Famille", ordering="famille__nom_famille")
    def famille_display(self, obj):
        if not obj.famille_id:
            return self._muted("Sans famille")
        return obj.famille.nom_famille

    @admin.display(description="Village", ordering="famille__village__nom")
    def village_display(self, obj):
        if not obj.famille_id:
            return self._muted("Non renseigne")
        return obj.famille.village.nom

    @admin.display(description="Genre", ordering="genre")
    def genre_badge_display(self, obj):
        bg, color, label = self.GENRE_COLORS.get(
            obj.genre,
            ("#F1EFE8", "#444441", obj.genre or "Inconnu"),
        )
        return self._badge(label, bg, color)

    @admin.display(description="Age")
    def age_display(self, obj):
        if obj.age is None:
            return self._muted("Inconnu")
        return f"{obj.age} an(s)"

    @admin.display(description="Situation", ordering="situation_matrimoniale")
    def situation_badge_display(self, obj):
        bg, color = self.SITUATION_COLORS.get(
            obj.situation_matrimoniale,
            ("#F1EFE8", "#444441"),
        )
        return self._badge(obj.get_situation_matrimoniale_display(), bg, color)

    @admin.display(description="Residence", ordering="type_residence")
    def residence_badge_display(self, obj):
        bg, color = self.RESIDENCE_COLORS.get(
            obj.type_residence,
            ("#F1EFE8", "#444441"),
        )
        return self._badge(obj.get_type_residence_display(), bg, color)

    @admin.display(description="Statut", ordering="est_vivant")
    def est_vivant_badge_display(self, obj):
        if obj.est_vivant:
            return self._badge("Vivant(e)", "#E1F5EE", "#0F6E56")
        return self._badge("Decede(e)", "#FAECE7", "#712B13")

    @admin.display(description="Parents")
    def parents_display(self, obj):
        parents = []
        if obj.pere:
            parents.append(f"Pere : {obj.pere.nom_complet}")
        elif obj.pere_nom_libre:
            parents.append(f"Pere : {obj.pere_nom_libre}")
        if obj.mere:
            parents.append(f"Mere : {obj.mere.nom_complet}")
        elif obj.mere_nom_libre:
            parents.append(f"Mere : {obj.mere_nom_libre}")
        if not parents:
            return self._muted("Non renseignes")
        return format_html("{}", "<br>".join(parents))

    @admin.display(description="Conjoint(e)")
    def conjoint_display(self, obj):
        if obj.conjoint:
            return obj.conjoint.nom_complet
        if obj.conjoint_nom_libre:
            return obj.conjoint_nom_libre
        return self._muted("Non renseigne")

    @admin.display(description="Generation")
    def generation_display(self, obj):
        return obj.generation

    @admin.display(boolean=True, description="Chef de famille")
    def est_chef_famille_display(self, obj):
        return obj.est_chef_famille

    @admin.display(boolean=True, description="Profil diaspora")
    def a_profil_diaspora_display(self, obj):
        return obj.a_profil_diaspora

    @admin.display(description="Photo")
    def photo_preview(self, obj):
        if not obj or not obj.photo:
            return self._muted("Aucune photo")
        try:
            return format_html(
                '<img src="{}" alt="{}" style="max-height:120px;border-radius:8px;" />',
                obj.photo.url,
                obj.nom_complet,
            )
        except Exception:
            return self._muted("Fichier indisponible")

    @admin.action(description="Exporter en CSV")
    def exporter_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="personnes_olodio.csv"'
        response.write("\ufeff")

        writer = csv.writer(response)
        writer.writerow(
            [
                "ID",
                "Code",
                "Nom",
                "Prenom",
                "Surnom",
                "Genre",
                "Date naissance",
                "Age",
                "Situation matrimoniale",
                "Est vivant",
                "Date deces",
                "Telephone",
                "Email",
                "Profession",
                "Type residence",
                "Lieu residence",
                "Famille",
                "Village",
                "Pere",
                "Mere",
                "Conjoint",
                "Generation",
                "Notes",
                "Date creation",
                "Date mise a jour",
            ]
        )

        for person in queryset.select_related("famille__village", "pere", "mere", "conjoint"):
            writer.writerow(
                [
                    str(person.id),
                    person.code or "",
                    person.nom,
                    person.prenom,
                    person.surnom or "",
                    person.get_genre_display(),
                    person.date_naissance.strftime("%d/%m/%Y")
                    if person.date_naissance
                    else "",
                    person.age if person.age is not None else "",
                    person.get_situation_matrimoniale_display(),
                    "Oui" if person.est_vivant else "Non",
                    person.date_deces.strftime("%d/%m/%Y") if person.date_deces else "",
                    person.telephone or "",
                    person.email or "",
                    person.profession or "",
                    person.get_type_residence_display(),
                    person.lieu_residence or "",
                    person.famille.nom_famille if person.famille_id else "",
                    person.famille.village.nom if person.famille_id else "",
                    person.pere.nom_complet if person.pere else (person.pere_nom_libre or ""),
                    person.mere.nom_complet if person.mere else (person.mere_nom_libre or ""),
                    person.conjoint.nom_complet if person.conjoint else (person.conjoint_nom_libre or ""),
                    person.generation,
                    person.notes or "",
                    person.date_creation.strftime("%d/%m/%Y %H:%M"),
                    person.date_maj.strftime("%d/%m/%Y %H:%M"),
                ]
            )

        return response
