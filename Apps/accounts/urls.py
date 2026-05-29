from django.urls import include, path
from . import auth_urls

urlpatterns = [
    path('', include(auth_urls)),
]
