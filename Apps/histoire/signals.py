from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from Apps.histoire.services import create_action_history


@receiver(user_logged_in, dispatch_uid='histoire_log_user_login')
def log_user_login(sender, request, user, **kwargs):
    create_action_history(
        user=user,
        request=request,
        fonction='accounts:login',
        action='Connexion',
        methode='POST',
        chemin=getattr(request, 'path', '/accounts/login/'),
        statut_code=200,
    )


@receiver(user_logged_out, dispatch_uid='histoire_log_user_logout')
def log_user_logout(sender, request, user, **kwargs):
    create_action_history(
        user=user,
        request=request,
        fonction='accounts:logout',
        action='Déconnexion',
        methode='POST',
        chemin=getattr(request, 'path', '/accounts/logout/'),
        statut_code=200,
    )
