from django.contrib import admin

from Apps.cotisations.models import (
    ComptePaiement,
    Cotisation,
    CotisationPersonne,
    Paiement,
)


@admin.register(ComptePaiement)
class ComptePaiementAdmin(admin.ModelAdmin):
    list_display = ("mode", "numero", "nom_titulaire", "est_actif", "ordre_affichage")
    list_filter = ("mode", "est_actif")
    search_fields = ("numero", "nom_titulaire", "instructions")
    ordering = ("ordre_affichage", "mode", "nom_titulaire")


@admin.register(Cotisation)
class CotisationAdmin(admin.ModelAdmin):
    list_display = (
        "periode_label",
        "cible_label",
        "est_generale",
        "statut",
        "nombre_personnes_cibles",
        "nombre_payeurs",
        "total_collecte",
    )
    list_filter = ("est_generale", "statut", "annee", "mois", "village")
    search_fields = ("description", "famille__nom_famille", "village__nom")
    autocomplete_fields = ("village", "famille")


@admin.register(CotisationPersonne)
class CotisationPersonneAdmin(admin.ModelAdmin):
    list_display = (
        "cotisation",
        "personne",
        "montant_attendu",
        "total_paye",
        "reste_a_payer",
        "statut_suivi_label",
    )
    list_filter = ("cotisation__annee", "cotisation__mois", "cotisation__village")
    search_fields = (
        "personne__nom",
        "personne__prenom",
        "cotisation__description",
        "notes",
    )
    autocomplete_fields = ("cotisation", "personne")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "cotisation",
            "personne",
            "personne__famille",
            "personne__famille__village",
        )


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = (
        "personne",
        "cotisation",
        "montant",
        "mode_paiement",
        "est_soumission_publique",
        "statut_validation",
        "date_paiement",
    )
    list_filter = (
        "est_soumission_publique",
        "statut_validation",
        "mode_paiement",
        "date_paiement",
    )
    search_fields = (
        "personne__nom",
        "personne__prenom",
        "reference_transaction",
        "nom_soumetteur",
        "telephone_soumetteur",
        "email_soumetteur",
        "notes",
    )
    autocomplete_fields = ("personne", "cotisation", "compte_paiement", "enregistre_par", "valide_par")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "personne",
            "cotisation",
            "compte_paiement",
        )
