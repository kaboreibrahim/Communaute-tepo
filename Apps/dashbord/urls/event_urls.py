from django.urls import path

from Apps.dashbord.views.event_views import (
    EventCreateView,
    EventListView,
    EventUpdateView,
    TypeEvenementCreateView,
    TypeEvenementDeleteView,
    TypeEvenementDetailView,
    TypeEvenementListView,
    TypeEvenementUpdateView,
)

urlpatterns = [
    path("evenements/", EventListView.as_view(), name="event-list"),
    path("evenements/ajouter/", EventCreateView.as_view(), name="event-create"),
    path(
        "evenements/<int:event_id>/modifier/",
        EventUpdateView.as_view(),
        name="event-update",
    ),
    # TypeEvenement CRUD
    path("evenements/types/", TypeEvenementListView.as_view(), name="type-evenement-list"),
    path("evenements/types/ajouter/", TypeEvenementCreateView.as_view(), name="type-evenement-create"),
    path("evenements/types/<int:type_id>/", TypeEvenementDetailView.as_view(), name="type-evenement-detail"),
    path("evenements/types/<int:type_id>/modifier/", TypeEvenementUpdateView.as_view(), name="type-evenement-update"),
    path("evenements/types/<int:type_id>/supprimer/", TypeEvenementDeleteView.as_view(), name="type-evenement-delete"),
]
