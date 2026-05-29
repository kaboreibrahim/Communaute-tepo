from django.urls import path

from Apps.dashbord.views.user_views import UserCreateView, UserListView

urlpatterns = [
    path("utilisateurs/", UserListView.as_view(), name="user-list"),
    path("utilisateurs/ajouter/", UserCreateView.as_view(), name="user-create"),
]
