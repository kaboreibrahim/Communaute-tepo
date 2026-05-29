from django.urls import path
from Apps.medias.views import (
    MediaDashboardView,
    MediaListView,
    MediaUploadView,
    MediaDetailView,
    MediaUpdateView,
    MediaDeleteView,
    media_delete_ajax,
    CategorieListView,
    CategorieCreateView,
    CategorieUpdateView,
    CategorieDeleteView,
)

app_name = 'medias'

urlpatterns = [
    path('', MediaDashboardView.as_view(), name='dashboard'),
    path('bibliotheque/', MediaListView.as_view(), name='media-list'),
    path('upload/', MediaUploadView.as_view(), name='media-upload'),
    path('<uuid:pk>/', MediaDetailView.as_view(), name='media-detail'),
    path('<uuid:pk>/modifier/', MediaUpdateView.as_view(), name='media-update'),
    path('<uuid:pk>/supprimer/', MediaDeleteView.as_view(), name='media-delete'),
    path('<uuid:pk>/supprimer/ajax/', media_delete_ajax, name='media-delete-ajax'),
    path('categories/', CategorieListView.as_view(), name='categorie-list'),
    path('categories/creer/', CategorieCreateView.as_view(), name='categorie-create'),
    path('categories/<int:pk>/modifier/', CategorieUpdateView.as_view(), name='categorie-update'),
    path('categories/<int:pk>/supprimer/', CategorieDeleteView.as_view(), name='categorie-delete'),
]
