from django.urls import path
from Apps.dashbord.views.website_images_views import (
    AccueilImageListView,
    AccueilImageCreateView,
    AccueilImageUpdateView,
    AccueilImageDeleteView,
    AccueilImageToggleView,
)

urlpatterns = [
    path("site/images/", AccueilImageListView.as_view(), name="site-images-list"),
    path("site/images/ajouter/", AccueilImageCreateView.as_view(), name="site-images-create"),
    path("site/images/<int:pk>/modifier/", AccueilImageUpdateView.as_view(), name="site-images-update"),
    path("site/images/<int:pk>/supprimer/", AccueilImageDeleteView.as_view(), name="site-images-delete"),
    path("site/images/<int:pk>/toggle/", AccueilImageToggleView.as_view(), name="site-images-toggle"),
]
