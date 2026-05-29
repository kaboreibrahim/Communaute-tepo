from ipaddress import ip_address

from django.conf import settings

from Apps.histoire.models import ActionHistory


COUNTRY_HEADER_KEYS = (
    'HTTP_CF_IPCOUNTRY',
    'HTTP_X_COUNTRY_CODE',
    'HTTP_X_COUNTRY',
    'HTTP_GEOIP_COUNTRY_NAME',
    'HTTP_X_APPENGINE_COUNTRY',
)

CITY_HEADER_KEYS = (
    'HTTP_X_CITY',
    'HTTP_GEOIP_CITY',
    'HTTP_X_APPENGINE_CITY',
    'HTTP_CF_IPCITY',
)


def _get_user_name(user) -> str:
    if not user or not getattr(user, 'is_authenticated', False):
        return "Utilisateur anonyme"

    if hasattr(user, 'get_full_name'):
        full_name = (user.get_full_name() or '').strip()
        if full_name:
            return full_name

    return getattr(user, 'username', '') or getattr(user, 'email', '') or "Utilisateur"


def _get_user_role(user) -> str:
    if not user or not getattr(user, 'is_authenticated', False):
        return ""
    if hasattr(user, 'get_role_display'):
        return user.get_role_display()
    return getattr(user, 'role', '') or ''


def get_client_ip(request) -> str:
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '').strip()


def _read_meta_value(request, keys) -> str:
    for key in keys:
        value = (request.META.get(key) or '').strip()
        if value:
            return value
    return ''


def _is_local_ip(raw_ip: str) -> bool:
    if not raw_ip:
        return False

    try:
        parsed_ip = ip_address(raw_ip)
    except ValueError:
        return False

    return (
        parsed_ip.is_loopback
        or parsed_ip.is_private
        or parsed_ip.is_reserved
        or parsed_ip.is_link_local
    )


def resolve_location(request, raw_ip: str) -> tuple[str, str]:
    if _is_local_ip(raw_ip):
        return "Réseau local", "Local"

    country = _read_meta_value(request, COUNTRY_HEADER_KEYS)
    city = _read_meta_value(request, CITY_HEADER_KEYS)

    if country and city:
        return country, city

    try:
        from django.contrib.gis.geoip2 import GeoIP2

        geoip_kwargs = {}
        geoip_path = getattr(settings, 'GEOIP_PATH', '')
        if geoip_path:
            geoip_kwargs['path'] = geoip_path

        geoip = GeoIP2(**geoip_kwargs)
        geo_data = geoip.city(raw_ip)
        country = country or geo_data.get('country_name') or geo_data.get('country_code') or ''
        city = city or geo_data.get('city') or ''
    except Exception:
        pass

    return country or "Inconnu", city or "Inconnu"


def infer_function_and_action(request) -> tuple[str, str]:
    resolver_match = getattr(request, 'resolver_match', None)
    view_name = getattr(resolver_match, 'view_name', '') or request.path
    url_name = (getattr(resolver_match, 'url_name', '') or '').lower()
    path = (request.path or '').lower()
    method = request.method.upper()

    if method == 'GET':
        action = 'Consultation'
    elif url_name == 'login' or '/login/' in path:
        action = 'Connexion'
    elif url_name == 'logout' or '/logout/' in path:
        action = 'Déconnexion'
    elif 'delete' in url_name or 'supprimer' in path:
        action = 'Suppression'
    elif 'update' in url_name or 'modifier' in path:
        action = 'Modification'
    elif 'create' in url_name or 'ajouter' in path:
        action = 'Création'
    else:
        action = 'Soumission'

    return view_name, action


def should_log_request(request) -> bool:
    if request.method in {'HEAD', 'OPTIONS'}:
        return False

    if not getattr(request.user, 'is_authenticated', False):
        return False

    resolver_match = getattr(request, 'resolver_match', None)
    if resolver_match is None:
        return False

    view_name = getattr(resolver_match, 'view_name', '') or ''
    if view_name in {'accounts:login', 'accounts:logout'}:
        return False

    path = request.path or ''
    for prefix in (settings.STATIC_URL, settings.MEDIA_URL):
        if prefix and path.startswith(prefix):
            return False

    return True


def create_action_history(
    *,
    user=None,
    request=None,
    fonction='',
    action='',
    methode='',
    chemin='',
    statut_code=None,
):
    if request is not None:
        fonction = fonction or infer_function_and_action(request)[0]
        action = action or infer_function_and_action(request)[1]
        methode = methode or request.method.upper()
        chemin = chemin or request.path
        adresse_ip = get_client_ip(request)
        pays, ville = resolve_location(request, adresse_ip)
    else:
        adresse_ip = None
        pays, ville = "Inconnu", "Inconnu"

    ActionHistory.objects.create(
        user=user if getattr(user, 'is_authenticated', False) else None,
        user_name=_get_user_name(user),
        user_role=_get_user_role(user),
        fonction=fonction or 'action_inconnue',
        action=action or 'Action',
        methode=methode or '',
        chemin=chemin or '',
        statut_code=statut_code,
        adresse_ip=adresse_ip,
        pays=pays,
        ville=ville,
    )


def log_request_action(request, response):
    create_action_history(
        user=getattr(request, 'user', None),
        request=request,
        statut_code=getattr(response, 'status_code', None),
    )
