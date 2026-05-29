from django.urls import path
from Apps.dashbord.views.dashbord_admin import admin_dashboard, admin_search

urlpatterns = [
    path('admin/', admin_dashboard, name='admin_dashboard'),
    path('recherche/', admin_search, name='search'),
]
