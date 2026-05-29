import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.utils.http import url_has_allowed_host_and_scheme

logger = logging.getLogger(__name__)


class AuthService:

    @staticmethod
    def complete_login(request, user, next_url=None):
        redirect_url = AuthService.get_redirect_url(request, next_url)
        login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0])
        user_name = user.get_full_name() or user.username
        messages.success(request, f"Bienvenue {user_name} ! Vous etes connecte.")
        return redirect_url

    @staticmethod
    def get_redirect_url(request, next_url=None):
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return next_url
        return "dashbord:admin_dashboard"
