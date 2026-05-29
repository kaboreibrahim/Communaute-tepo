from django.contrib import admin
from django.utils.html import format_html

from Apps.website.models import AccueilImage, PublicPersonSubmission


@admin.register(AccueilImage)
class AccueilImageAdmin(admin.ModelAdmin):
    list_display = (
        "apercu",
        "section",
        "titre",
        "ordre",
        "est_active",
        "date_creation",
    )
    list_filter = ("section", "est_active")
    search_fields = ("titre", "sous_titre", "texte_alt", "image_url")
    list_editable = ("ordre", "est_active")
    ordering = ("section", "ordre", "-date_creation")

    def apercu(self, obj):
        if not obj.source_url:
            return "-"
        return format_html(
            '<img src="{}" alt="{}" style="height: 48px; width: 72px; '
            'object-fit: cover; border-radius: 8px;" />',
            obj.source_url,
            obj.texte_alt or obj.titre or "Image d'accueil",
        )

    apercu.short_description = "Apercu"


@admin.register(PublicPersonSubmission)
class PublicPersonSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "date_creation",
        "nom_complet",
        "statut_validation",
        "famille",
        "valide_par",
        "date_validation",
        "personne_creee",
    )
    list_filter = ("statut_validation", "genre", "type_residence", "famille__village")
    search_fields = (
        "nom",
        "prenom",
        "surnom",
        "telephone",
        "email",
        "numero_cni",
        "famille__nom_famille",
        "famille__village__nom",
    )
