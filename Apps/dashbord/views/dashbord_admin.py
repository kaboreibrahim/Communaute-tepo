from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render

from Apps.dashbord.security import (
    filter_person_queryset_for_user,
    is_limited_data_entry_agent,
)
from Apps.families.models import Family
from Apps.person.models import Person
from Apps.villages.models import Village


BAR_COLOR_CLASSES = [
    "bg-primary/20",
    "bg-primary/30",
    "bg-primary/50",
    "bg-primary/70",
    "bg-primary/30",
    "bg-primary/40",
    "bg-primary/60",
    "bg-primary/80",
]

SEARCH_RESULTS_LIMIT = 6


def _format_number(value: int) -> str:
    return f"{int(value):,}".replace(",", " ")


def _format_decimal(value: float, precision: int = 1) -> str:
    formatted = f"{value:,.{precision}f}"
    formatted = formatted.replace(",", " ").replace(".", ",")
    return formatted.rstrip("0").rstrip(",")


def _percentage(part: int, total: int, precision: int = 1) -> float:
    if not total:
        return 0
    return round((part / total) * 100, precision)


def _build_initials(value: str) -> str:
    parts = [part[0].upper() for part in str(value).split() if part]
    return "".join(parts[:2]) or "NA"


def _build_stats_cards(dashboard_stats: dict) -> list[dict]:
    return [
        {
            "label": "Population recensee",
            "value": dashboard_stats["total_personnes_display"],
            "badge": f'{dashboard_stats["total_vivants_display"]} vivants',
            "icon": "groups",
            "icon_classes": "bg-primary/10 text-primary",
            "badge_classes": "bg-emerald-100 text-emerald-700",
            "caption": "Total des personnes enregistrees dans le registre.",
        },
        {
            "label": "Familles actives",
            "value": dashboard_stats["total_familles_display"],
            "badge": f'{dashboard_stats["verification_rate_display"]}% verifiees',
            "icon": "house",
            "icon_classes": "bg-primary/10 text-primary",
            "badge_classes": "bg-blue-100 text-blue-700",
            "caption": "Foyers relies a un chef de famille identifie.",
        },
        {
            "label": "Villages enregistres",
            "value": dashboard_stats["total_villages_display"],
            "badge": f'{dashboard_stats["villages_with_population_display"]} avec donnees',
            "icon": "map",
            "icon_classes": "bg-primary/10 text-primary",
            "badge_classes": "bg-slate-100 text-slate-700",
            "caption": "Villages relies a au moins une personne recensee.",
        },
        {
            "label": "Membres diaspora",
            "value": dashboard_stats["total_diaspora_display"],
            "badge": f'{dashboard_stats["diaspora_rate_display"]}% du registre',
            "icon": "language",
            "icon_classes": "bg-primary/10 text-primary",
            "badge_classes": "bg-amber-100 text-amber-700",
            "caption": "Personnes ayant une residence renseignee en diaspora.",
        },
    ]


def _visible_persons_queryset(user):
    return filter_person_queryset_for_user(
        Person.objects.filter(
            deleted__isnull=True,
            famille__deleted__isnull=True,
            famille__village__deleted__isnull=True,
        ),
        user,
    )


def _visible_families_queryset(user):
    qs = Family.objects.filter(
        deleted__isnull=True,
        village__deleted__isnull=True,
    )
    if is_limited_data_entry_agent(user):
        qs = qs.filter(
            membres__deleted__isnull=True,
            membres__created_by=user,
        ).distinct()
    return qs


def _visible_villages_queryset(user):
    qs = Village.objects.filter(deleted__isnull=True)
    if is_limited_data_entry_agent(user):
        qs = qs.filter(
            familles__membres__deleted__isnull=True,
            familles__membres__created_by=user,
        ).distinct()
    return qs


def _build_village_population_rows(user) -> tuple[list[dict], int]:
    population_filter = Q(
        familles__deleted__isnull=True,
        familles__membres__deleted__isnull=True,
    )
    family_filter = Q(familles__deleted__isnull=True)
    villages = _visible_villages_queryset(user)

    if is_limited_data_entry_agent(user):
        population_filter &= Q(familles__membres__created_by=user)
        family_filter &= Q(
            familles__membres__deleted__isnull=True,
            familles__membres__created_by=user,
        )

    villages = list(
        villages
        .annotate(
            total_population=Count(
                "familles__membres",
                filter=population_filter,
                distinct=True,
            ),
            total_families=Count(
                "familles",
                filter=family_filter,
                distinct=True,
            ),
        )
        .order_by("-total_population", "nom")[:8]
    )

    max_population = max(
        (village.total_population for village in villages),
        default=0,
    )
    rows = []

    for index, village in enumerate(villages):
        bar_height = 0
        if max_population and village.total_population:
            bar_height = max(
                int(round((village.total_population / max_population) * 100)),
                16,
            )

        rows.append(
            {
                "nom": village.nom,
                "total_population": village.total_population,
                "total_population_display": _format_number(village.total_population),
                "total_families": village.total_families,
                "total_families_display": _format_number(village.total_families),
                "bar_height": bar_height,
                "bar_classes": BAR_COLOR_CLASSES[index % len(BAR_COLOR_CLASSES)],
            }
        )

    return rows, max_population


def _build_recent_family_rows(user) -> list[dict]:
    recent_families = list(
        _visible_families_queryset(user)
        .select_related("village")
        .annotate(
            members_count=Count(
                "membres",
                filter=Q(membres__deleted__isnull=True)
                & (
                    Q()
                    if not is_limited_data_entry_agent(user)
                    else Q(membres__created_by=user)
                ),
                distinct=True,
            ),
            verified_heads=Count(
                "membres",
                filter=Q(
                    membres__deleted__isnull=True,
                    membres__est_chef_famille=True,
                )
                & (
                    Q()
                    if not is_limited_data_entry_agent(user)
                    else Q(membres__created_by=user)
                ),
                distinct=True,
            ),
        )
        .order_by("-date_creation")[:5]
    )

    family_ids = [family.id for family in recent_families]
    if not family_ids:
        return []

    visible_persons = _visible_persons_queryset(user).filter(famille_id__in=family_ids)
    family_heads = {}
    for head in (
        visible_persons.filter(
            est_chef_famille=True,
        )
        .order_by("famille_id", "date_creation", "nom", "prenom")
    ):
        family_heads.setdefault(head.famille_id, head)

    family_fallbacks = {}
    for person in (
        visible_persons
        .order_by("famille_id", "date_creation", "nom", "prenom")
    ):
        family_fallbacks.setdefault(person.famille_id, person)

    rows = []
    for family in recent_families:
        head = family_heads.get(family.id) or family_fallbacks.get(family.id)
        head_name = head.nom_complet if head else family.nom_famille
        is_verified = family.verified_heads > 0

        rows.append(
            {
                "family_id": family.id,
                "family_name": family.nom_famille,
                "head_name": head_name,
                "head_initials": _build_initials(head_name),
                "village_name": family.village.nom,
                "members_count": family.members_count,
                "status_label": "Verifiee" if is_verified else "A completer",
                "status_classes": (
                    "bg-emerald-100 text-emerald-700"
                    if is_verified
                    else "bg-amber-100 text-amber-700"
                ),
                "date_added": family.date_creation,
            }
        )

    return rows


def _build_dashboard_context(user) -> dict:
    persons_qs = _visible_persons_queryset(user)
    families_qs = _visible_families_queryset(user)
    villages_qs = _visible_villages_queryset(user)

    person_stats = persons_qs.aggregate(
        total_personnes=Count("id"),
        total_vivants=Count("id", filter=Q(est_vivant=True)),
        total_diaspora=Count("id", filter=Q(type_residence="diaspora")),
        total_femmes=Count("id", filter=Q(genre="F")),
        total_hommes=Count("id", filter=Q(genre="M")),
    )

    total_personnes = person_stats["total_personnes"] or 0
    total_vivants = person_stats["total_vivants"] or 0
    total_diaspora = person_stats["total_diaspora"] or 0
    total_femmes = person_stats["total_femmes"] or 0
    total_hommes = person_stats["total_hommes"] or 0

    total_familles = families_qs.count()
    total_villages = villages_qs.count()
    familles_verifiees = (
        persons_qs.filter(
            est_chef_famille=True,
        )
        .values("famille_id")
        .distinct()
        .count()
    )
    villages_with_population = (
        persons_qs.values("famille__village_id").distinct().count()
    )

    verification_rate = _percentage(familles_verifiees, total_familles)
    diaspora_rate = _percentage(total_diaspora, total_personnes)
    female_percentage = _percentage(total_femmes, total_personnes)
    male_percentage = _percentage(total_hommes, total_personnes)

    dashboard_stats = {
        "total_personnes": total_personnes,
        "total_personnes_display": _format_number(total_personnes),
        "total_vivants": total_vivants,
        "total_vivants_display": _format_number(total_vivants),
        "total_familles": total_familles,
        "total_familles_display": _format_number(total_familles),
        "total_villages": total_villages,
        "total_villages_display": _format_number(total_villages),
        "total_diaspora": total_diaspora,
        "total_diaspora_display": _format_number(total_diaspora),
        "familles_verifiees": familles_verifiees,
        "familles_verifiees_display": _format_number(familles_verifiees),
        "villages_with_population": villages_with_population,
        "villages_with_population_display": _format_number(villages_with_population),
        "verification_rate": verification_rate,
        "verification_rate_display": _format_decimal(verification_rate),
        "diaspora_rate": diaspora_rate,
        "diaspora_rate_display": _format_decimal(diaspora_rate),
        "female_percentage": female_percentage,
        "female_percentage_display": _format_decimal(female_percentage),
        "male_percentage": male_percentage,
        "male_percentage_display": _format_decimal(male_percentage),
    }

    village_population_rows, max_population = _build_village_population_rows(user)

    gender_rows = [
        {
            "label": "Femmes",
            "count": total_femmes,
            "count_display": _format_number(total_femmes),
            "percentage": female_percentage,
            "percentage_display": _format_decimal(female_percentage),
            "width_value": f"{female_percentage:.1f}",
            "dot_classes": "bg-primary",
            "bar_classes": "bg-primary",
        },
        {
            "label": "Hommes",
            "count": total_hommes,
            "count_display": _format_number(total_hommes),
            "percentage": male_percentage,
            "percentage_display": _format_decimal(male_percentage),
            "width_value": f"{male_percentage:.1f}",
            "dot_classes": "bg-primary/25",
            "bar_classes": "bg-primary/25",
        },
    ]

    return {
        "title": "Tableau de bord administrateur",
        "dashboard_stats": dashboard_stats,
        "stats_cards": _build_stats_cards(dashboard_stats),
        "village_population_rows": village_population_rows,
        "village_chart_has_data": max_population > 0,
        "gender_rows": gender_rows,
        "gender_circle_value": f"{female_percentage:.1f}",
        "recent_family_rows": _build_recent_family_rows(user),
    }


def _normalize_query(value: str) -> str:
    return " ".join((value or "").split()).strip()


def _build_search_context(raw_query: str, user) -> dict:
    query = _normalize_query(raw_query)
    empty_context = {
        "search_query": query,
        "search_totals": {
            "all": 0,
            "villages": 0,
            "families": 0,
            "persons": 0,
        },
        "village_results": [],
        "family_results": [],
        "person_results": [],
    }

    limited_agent = is_limited_data_entry_agent(user)
    family_member_filter = Q(membres__deleted__isnull=True)
    village_person_filter = Q(
        familles__deleted__isnull=True,
        familles__membres__deleted__isnull=True,
    )
    village_family_filter = Q(familles__deleted__isnull=True)

    if limited_agent:
        family_member_filter &= Q(membres__created_by=user)
        village_person_filter &= Q(familles__membres__created_by=user)
        village_family_filter &= Q(
            familles__membres__deleted__isnull=True,
            familles__membres__created_by=user,
        )

    if not query:
        return empty_context

    villages_qs = (
        _visible_villages_queryset(user)
        .annotate(
            total_families=Count(
                "familles",
                filter=village_family_filter,
                distinct=True,
            ),
            total_personnes=Count(
                "familles__membres",
                filter=village_person_filter,
                distinct=True,
            ),
        )
        .filter(
            Q(nom__icontains=query)
            | Q(description__icontains=query)
            | Q(chef_village__icontains=query)
        )
        .order_by("nom")
    )

    families_qs = (
        _visible_families_queryset(user)
        .select_related("village")
        .annotate(
            members_count=Count(
                "membres",
                filter=family_member_filter,
                distinct=True,
            ),
        )
        .filter(
            Q(nom_famille__icontains=query)
            | Q(description__icontains=query)
            | Q(village__nom__icontains=query)
            | Q(
                family_member_filter,
                membres__nom__icontains=query,
            )
            | Q(
                family_member_filter,
                membres__prenom__icontains=query,
            )
        )
        .distinct()
        .order_by("nom_famille")
    )

    persons_qs = (
        _visible_persons_queryset(user)
        .select_related("famille__village")
        .filter(
            Q(code__icontains=query)
            | Q(nom__icontains=query)
            | Q(prenom__icontains=query)
            | Q(surnom__icontains=query)
            | Q(profession__icontains=query)
            | Q(pere_nom_libre__icontains=query)
            | Q(mere_nom_libre__icontains=query)
            | Q(conjoint_nom_libre__icontains=query)
            | Q(famille__nom_famille__icontains=query)
            | Q(famille__village__nom__icontains=query)
        )
        .order_by("prenom", "nom")
    )

    village_total = villages_qs.count()
    family_total = families_qs.count()
    person_total = persons_qs.count()

    village_results = [
        {
            "id": village.id,
            "nom": village.nom,
            "chef_village": village.chef_village or "Non renseigne",
            "description": (village.description or "").strip(),
            "total_families": village.total_families,
            "total_families_display": _format_number(village.total_families),
            "total_personnes": village.total_personnes,
            "total_personnes_display": _format_number(village.total_personnes),
        }
        for village in villages_qs[:SEARCH_RESULTS_LIMIT]
    ]

    family_results = []
    for family in families_qs[:SEARCH_RESULTS_LIMIT]:
        head = None
        if not limited_agent:
            head = family.chef
        if head is None:
            head = _visible_persons_queryset(user).filter(
                famille_id=family.id
            ).order_by("date_creation", "nom", "prenom").first()
        family_results.append(
            {
                "id": family.id,
                "nom_famille": family.nom_famille,
                "village_nom": family.village.nom,
                "chef_nom": head.nom_complet if head else "Non renseigne",
                "members_count": family.members_count,
                "members_count_display": _format_number(family.members_count),
            }
        )

    person_results = [
        {
            "id": person.id,
            "nom_complet": person.nom_complet,
            "code": person.code or "Sans code",
            "famille_nom": person.famille.nom_famille,
            "village_nom": person.famille.village.nom,
            "genre_label": person.get_genre_display(),
        }
        for person in persons_qs[:SEARCH_RESULTS_LIMIT]
    ]

    return {
        "search_query": query,
        "search_totals": {
            "all": village_total + family_total + person_total,
            "villages": village_total,
            "families": family_total,
            "persons": person_total,
        },
        "village_results": village_results,
        "family_results": family_results,
        "person_results": person_results,
    }


@login_required
def admin_dashboard(request):
    return render(
        request,
        "dashbord/admin_dashboard.html",
        _build_dashboard_context(request.user),
    )


@login_required
def admin_search(request):
    return render(
        request,
        "dashbord/search_results.html",
        {
            "title": "Recherche admin",
            **_build_search_context(request.GET.get("q", ""), request.user),
        },
    )
