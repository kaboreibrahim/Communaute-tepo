# dashboard/urls.py

from django.urls import path
from ..views.village_views import (
    VillageListView,
    VillageDetailView,
    VillageCreateView,
    VillageUpdateView,
    VillageDeleteView,
)

urlpatterns = [
    # Villages
    path('villages/',
         VillageListView.as_view(),
         name='village-list'),

    path('villages/ajouter/',
         VillageCreateView.as_view(),
         name='village-create'),

    path('villages/<uuid:village_id>/',
         VillageDetailView.as_view(),
         name='village-detail'),

    path('villages/<uuid:village_id>/modifier/',
         VillageUpdateView.as_view(),
         name='village-update'),

    path('villages/<uuid:village_id>/supprimer/',
         VillageDeleteView.as_view(),
         name='village-delete'),
]
