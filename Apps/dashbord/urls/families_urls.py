from django.urls import path
from Apps.dashbord.views.famille_views import FamilyListView, FamilyCreateView, FamilyDetailView, FamilyUpdateView, FamilyDeleteView

urlpatterns = [
    path('familles/',
         FamilyListView.as_view(),
         name='family-list'),
    path('familles/ajouter/',
         FamilyCreateView.as_view(),
         name='family-create'),
    path('familles/<uuid:family_id>/',
         FamilyDetailView.as_view(),
         name='family-detail'),
    path('familles/<uuid:family_id>/modifier/',
         FamilyUpdateView.as_view(),
         name='family-update'),
    path('familles/<uuid:family_id>/supprimer/',
         FamilyDeleteView.as_view(),
         name='family-delete'),
]