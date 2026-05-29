from django.urls import path

from Apps.dashbord.views.cotisation_views import (
    ComptePaiementCreateView,
    ComptePaiementListView,
    ComptePaiementUpdateView,
    CotisationCreateView,
    CotisationDetailView,
    CotisationPersonneUpdateView,
    CotisationListView,
    CotisationUpdateView,
    PaiementCreateView,
    PaiementUpdateView,
)


urlpatterns = [
    path("cotisations/", CotisationListView.as_view(), name="cotisation-list"),
    path("cotisations/ajouter/", CotisationCreateView.as_view(), name="cotisation-create"),
    path(
        "cotisations/<uuid:cotisation_id>/",
        CotisationDetailView.as_view(),
        name="cotisation-detail",
    ),
    path(
        "cotisations/<uuid:cotisation_id>/modifier/",
        CotisationUpdateView.as_view(),
        name="cotisation-update",
    ),
    path(
        "cotisations/<uuid:cotisation_id>/personnes/<uuid:person_id>/suivi/",
        CotisationPersonneUpdateView.as_view(),
        name="cotisation-person-tracking-update",
    ),
    path("paiements/ajouter/", PaiementCreateView.as_view(), name="paiement-create"),
    path(
        "paiements/<uuid:paiement_id>/modifier/",
        PaiementUpdateView.as_view(),
        name="paiement-update",
    ),
    path(
        "comptes-paiement/",
        ComptePaiementListView.as_view(),
        name="compte-paiement-list",
    ),
    path(
        "comptes-paiement/ajouter/",
        ComptePaiementCreateView.as_view(),
        name="compte-paiement-create",
    ),
    path(
        "comptes-paiement/<uuid:account_id>/modifier/",
        ComptePaiementUpdateView.as_view(),
        name="compte-paiement-update",
    ),
]
