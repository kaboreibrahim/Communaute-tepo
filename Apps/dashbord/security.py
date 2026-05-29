from django.core.exceptions import PermissionDenied

from Apps.person.models import Person


def is_limited_data_entry_agent(user) -> bool:
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "est_agent_saisie_limite", False)
    )


def can_manage_registry(user) -> bool:
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "est_agent_saisie", False)
    )


def can_delete_registry(user) -> bool:
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "peut_supprimer_registre", False)
    )


def ensure_registry_management(user) -> None:
    if can_manage_registry(user):
        return
    raise PermissionDenied(
        "Cette action est reservee aux administrateurs, chefs de village et agents de saisie."
    )


def ensure_registry_delete(user) -> None:
    if can_delete_registry(user):
        return
    raise PermissionDenied(
        "Les agents de saisie ne peuvent pas supprimer des enregistrements."
    )


def visible_person_creator_id(user) -> str:
    if is_limited_data_entry_agent(user):
        return str(user.id)
    return ""


def filter_person_queryset_for_user(queryset, user):
    if is_limited_data_entry_agent(user):
        return queryset.filter(created_by=user)
    return queryset


def ensure_person_access(user, person_id) -> None:
    if not is_limited_data_entry_agent(user):
        return

    has_access = Person.objects.filter(
        id=person_id,
        deleted__isnull=True,
        created_by=user,
    ).exists()
    if has_access:
        return

    raise PermissionDenied(
        "Vous ne pouvez consulter que les personnes que vous avez enregistrees."
    )
