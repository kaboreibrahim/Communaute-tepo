from django.urls import path
from Apps.accounts.views.auth_views import connexion, user_logout

app_name = 'accounts'

urlpatterns = [
    path('login/', connexion, name='login'),
    path('logout/', user_logout, name='logout'),
]
