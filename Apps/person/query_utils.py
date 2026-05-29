from django.db.models import Q


def parents_unknown_q(prefix: str = "") -> Q:
    """Return a Q object for records with no linked or free-text parents."""
    return (
        Q(**{f"{prefix}pere__isnull": True})
        & Q(**{f"{prefix}mere__isnull": True})
        & Q(**{f"{prefix}pere_nom_libre": ""})
        & Q(**{f"{prefix}mere_nom_libre": ""})
    )
