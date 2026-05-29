# dashboard/views/village_views.py
# ============================================================
#  Vue liste des villages — fournit toutes les données
#  nécessaires au template village_list.html
# ============================================================

from collections                      import Counter

from django.conf                      import settings
from django.shortcuts                 import render, redirect
from django.contrib                   import messages
from django.contrib.auth.decorators   import login_required
from django.utils.decorators          import method_decorator
from django.views                     import View
from django.core.paginator            import Paginator
from django.db.models                 import Q, Sum, Count

from Apps.villages.repositories.django_village_repo import DjangoVillageRepository
from Apps.villages.use_cases.list_villages   import ListVillagesUseCase
from Apps.villages.use_cases.get_village     import GetVillageUseCase
from Apps.villages.use_cases.create_village  import CreateVillageUseCase, VillageDejaExistantError
from Apps.villages.use_cases.update_village  import UpdateVillageUseCase, VillageIntrouvableError
from Apps.villages.use_cases.delete_village  import DeleteVillageUseCase
from Apps.villages.dtos.village_dto          import CreateVillageDTO, UpdateVillageDTO
from Apps.dashbord.security import (
    ensure_registry_delete,
    ensure_registry_management,
    filter_person_queryset_for_user,
    is_limited_data_entry_agent,
)

# Import direct du model uniquement pour les stats agrégées
from Apps.villages.models import Village, Infrastructure


def get_repo():
    return DjangoVillageRepository()


def _map_service_context() -> dict:
    return {
        'mapbox_token': getattr(settings, 'MAPBOX_ACCESS_TOKEN', ''),
        'locationiq_api_key': getattr(settings, 'LOCATIONIQ_API_KEY', ''),
    }


def _safe_positive_int(value, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _get_infrastructure_type_options() -> list:
    return [
        {
            'value': type_code,
            'label': type_label,
        }
        for type_code, type_label in Infrastructure.TYPES_INFRASTRUCTURE
    ]


def _get_infrastructure_state_options() -> list:
    return [
        {
            'value': state_code,
            'label': state_label,
        }
        for state_code, state_label in Infrastructure._meta.get_field('etat').choices
    ]


def _empty_infrastructure_form_row() -> dict:
    return {
        'id': '',
        'type_infrastructure': '',
        'nom': '',
        'etat': 'bon',
        'capacite': '',
        'responsable': '',
        'contact_responsable': '',
    }


def _build_infrastructure_form_rows(village_id=None, post_data=None) -> list:
    if post_data is not None:
        row_keys = (
            'infra_id',
            'infra_type',
            'infra_name',
            'infra_state',
            'infra_capacity',
            'infra_responsable',
            'infra_contact',
        )
        lists = {key: post_data.getlist(key) for key in row_keys}
        row_count = max((len(values) for values in lists.values()), default=0)
        rows = []

        for index in range(row_count):
            row = {
                'id': lists['infra_id'][index] if index < len(lists['infra_id']) else '',
                'type_infrastructure': lists['infra_type'][index] if index < len(lists['infra_type']) else '',
                'nom': lists['infra_name'][index] if index < len(lists['infra_name']) else '',
                'etat': lists['infra_state'][index] if index < len(lists['infra_state']) else 'bon',
                'capacite': lists['infra_capacity'][index] if index < len(lists['infra_capacity']) else '',
                'responsable': lists['infra_responsable'][index] if index < len(lists['infra_responsable']) else '',
                'contact_responsable': lists['infra_contact'][index] if index < len(lists['infra_contact']) else '',
            }
            rows.append(row)

        return rows or [_empty_infrastructure_form_row()]

    if village_id:
        rows = []
        for infra in Infrastructure.objects.filter(
            village_id=village_id,
            deleted__isnull=True,
        ).order_by('type_infrastructure', 'nom'):
            rows.append({
                'id': str(infra.id),
                'type_infrastructure': infra.type_infrastructure,
                'nom': infra.nom,
                'etat': infra.etat,
                'capacite': infra.capacite or '',
                'responsable': infra.responsable,
                'contact_responsable': infra.contact_responsable,
            })
        return rows or [_empty_infrastructure_form_row()]

    return [_empty_infrastructure_form_row()]


def _normalize_infrastructure_form_rows(post_data) -> list:
    valid_types = {code for code, _ in Infrastructure.TYPES_INFRASTRUCTURE}
    valid_states = {
        code for code, _ in Infrastructure._meta.get_field('etat').choices
    }
    labels_by_type = dict(Infrastructure.TYPES_INFRASTRUCTURE)
    normalized_rows = []

    for row in _build_infrastructure_form_rows(post_data=post_data):
        raw_type = (row.get('type_infrastructure') or '').strip()
        raw_name = (row.get('nom') or '').strip()
        raw_capacity = (row.get('capacite') or '').strip()
        raw_responsable = (row.get('responsable') or '').strip()
        raw_contact = (row.get('contact_responsable') or '').strip()

        if not any([raw_type, raw_name, raw_capacity, raw_responsable, raw_contact]):
            continue

        type_code = raw_type if raw_type in valid_types else 'autre'
        state_code = row.get('etat') if row.get('etat') in valid_states else 'bon'
        capacity = _safe_int(raw_capacity, 0)

        normalized_rows.append({
            'id': (row.get('id') or '').strip(),
            'type_infrastructure': type_code,
            'nom': raw_name or labels_by_type.get(type_code, 'Autre'),
            'etat': state_code,
            'capacite': capacity if capacity > 0 else None,
            'responsable': raw_responsable,
            'contact_responsable': raw_contact,
        })

    return normalized_rows


def _sync_village_infrastructures(village_id, infrastructure_rows) -> None:
    village = Village.objects.get(id=village_id, deleted__isnull=True)
    existing_infras = {
        str(infra.id): infra
        for infra in village.infrastructures.filter(deleted__isnull=True)
    }
    kept_ids = set()

    for row in infrastructure_rows:
        infra = existing_infras.get(row['id']) if row.get('id') else None
        if infra is None:
            infra = Infrastructure(village=village)

        infra.type_infrastructure = row['type_infrastructure']
        infra.nom = row['nom']
        infra.etat = row['etat']
        infra.capacite = row['capacite']
        infra.responsable = row['responsable']
        infra.contact_responsable = row['contact_responsable']
        infra.save()
        kept_ids.add(str(infra.id))

    for infra_id, infra in existing_infras.items():
        if infra_id not in kept_ids:
            infra.delete()


def _infra_ui_meta(type_code: str) -> dict:
    meta = {
        'ecole': {
            'icon': 'school',
            'badge_classes': 'bg-blue-100 text-blue-700',
            'bar_classes': 'bg-blue-500',
        },
        'ecole_maternelle': {
            'icon': 'school',
            'badge_classes': 'bg-sky-100 text-sky-700',
            'bar_classes': 'bg-sky-500',
        },
        'lycee': {
            'icon': 'menu_book',
            'badge_classes': 'bg-indigo-100 text-indigo-700',
            'bar_classes': 'bg-indigo-500',
        },
        'universite': {
            'icon': 'account_balance',
            'badge_classes': 'bg-violet-100 text-violet-700',
            'bar_classes': 'bg-violet-500',
        },
        'hopital': {
            'icon': 'local_hospital',
            'badge_classes': 'bg-red-100 text-red-700',
            'bar_classes': 'bg-red-500',
        },
        'dispensaire': {
            'icon': 'medical_services',
            'badge_classes': 'bg-rose-100 text-rose-700',
            'bar_classes': 'bg-rose-500',
        },
        'centre_sante': {
            'icon': 'health_and_safety',
            'badge_classes': 'bg-orange-100 text-orange-700',
            'bar_classes': 'bg-orange-500',
        },
        'marche': {
            'icon': 'storefront',
            'badge_classes': 'bg-emerald-100 text-emerald-700',
            'bar_classes': 'bg-emerald-500',
        },
        'poste_police': {
            'icon': 'local_police',
            'badge_classes': 'bg-slate-200 text-slate-700',
            'bar_classes': 'bg-slate-500',
        },
        'mairie': {
            'icon': 'location_city',
            'badge_classes': 'bg-amber-100 text-amber-700',
            'bar_classes': 'bg-amber-500',
        },
        'place_publique': {
            'icon': 'park',
            'badge_classes': 'bg-lime-100 text-lime-700',
            'bar_classes': 'bg-lime-500',
        },
        'centre_communautaire': {
            'icon': 'groups',
            'badge_classes': 'bg-cyan-100 text-cyan-700',
            'bar_classes': 'bg-cyan-500',
        },
        'puit': {
            'icon': 'water_drop',
            'badge_classes': 'bg-cyan-100 text-cyan-700',
            'bar_classes': 'bg-cyan-500',
        },
        'forage': {
            'icon': 'water',
            'badge_classes': 'bg-teal-100 text-teal-700',
            'bar_classes': 'bg-teal-500',
        },
        'electricite': {
            'icon': 'bolt',
            'badge_classes': 'bg-yellow-100 text-yellow-700',
            'bar_classes': 'bg-yellow-500',
        },
        'telephone': {
            'icon': 'call',
            'badge_classes': 'bg-fuchsia-100 text-fuchsia-700',
            'bar_classes': 'bg-fuchsia-500',
        },
        'internet': {
            'icon': 'wifi',
            'badge_classes': 'bg-purple-100 text-purple-700',
            'bar_classes': 'bg-purple-500',
        },
        'autre': {
            'icon': 'category',
            'badge_classes': 'bg-slate-100 text-slate-700',
            'bar_classes': 'bg-slate-500',
        },
    }
    return meta.get(type_code, meta['autre'])


def _etat_ui_meta(state_code: str) -> dict:
    meta = {
        'bon': {
            'badge_classes': 'bg-emerald-100 text-emerald-700',
            'bar_classes': 'bg-emerald-500',
        },
        'moyen': {
            'badge_classes': 'bg-amber-100 text-amber-700',
            'bar_classes': 'bg-amber-500',
        },
        'mauvais': {
            'badge_classes': 'bg-red-100 text-red-700',
            'bar_classes': 'bg-red-500',
        },
        'en_construction': {
            'badge_classes': 'bg-blue-100 text-blue-700',
            'bar_classes': 'bg-blue-500',
        },
        'abandonne': {
            'badge_classes': 'bg-slate-200 text-slate-700',
            'bar_classes': 'bg-slate-500',
        },
    }
    return meta.get(state_code, meta['mauvais'])


def _build_infrastructure_type_stats(infrastructures: list) -> list:
    total = len(infrastructures)
    counts = Counter(infra.type_infrastructure for infra in infrastructures)
    labels = dict(Infrastructure.TYPES_INFRASTRUCTURE)
    stats = []

    for type_code, count in counts.most_common():
        ui_meta = _infra_ui_meta(type_code)
        stats.append({
            'code': type_code,
            'label': labels.get(type_code, type_code.replace('_', ' ').title()),
            'count': count,
            'percent': int(round((count / total) * 100)) if total else 0,
            'icon': ui_meta['icon'],
            'badge_classes': ui_meta['badge_classes'],
            'bar_classes': ui_meta['bar_classes'],
        })

    return stats


def _build_infrastructure_state_stats(infrastructures: list) -> list:
    total = len(infrastructures)
    counts = Counter(infra.etat for infra in infrastructures)
    labels = dict(Infrastructure._meta.get_field('etat').choices)
    stats = []

    for state_code, count in counts.most_common():
        ui_meta = _etat_ui_meta(state_code)
        stats.append({
            'code': state_code,
            'label': labels.get(state_code, state_code.replace('_', ' ').title()),
            'count': count,
            'percent': int(round((count / total) * 100)) if total else 0,
            'badge_classes': ui_meta['badge_classes'],
            'bar_classes': ui_meta['bar_classes'],
        })

    return stats


def _build_recent_infrastructure_rows(infrastructures: list) -> list:
    recent_rows = []

    for infra in sorted(infrastructures, key=lambda item: item.date_creation, reverse=True)[:4]:
        ui_meta = _infra_ui_meta(infra.type_infrastructure)
        recent_rows.append({
            'icon': ui_meta['icon'],
            'icon_classes': ui_meta['badge_classes'],
            'name': infra.nom,
            'type_label': infra.get_type_infrastructure_display(),
            'created_at': infra.date_creation,
            'state_label': infra.get_etat_display(),
        })

    return recent_rows


def _build_family_rows(familles_manager, user=None) -> list:
    if familles_manager is None:
        return []

    family_rows = []
    for famille in familles_manager.all():
        membres = getattr(famille, 'membres', None)
        if membres is not None:
            membres_qs = membres.filter(deleted__isnull=True)
            if user is not None:
                membres_qs = filter_person_queryset_for_user(membres_qs, user)
            members_count = membres_qs.count()
        else:
            members_count = getattr(famille, 'nombre_membres', 0) or 0

        head_name = ''
        if user is not None and is_limited_data_entry_agent(user) and membres is not None:
            visible_head = membres_qs.filter(
                est_chef_famille=True
            ).order_by('date_creation', 'nom', 'prenom').first() or membres_qs.order_by(
                'date_creation', 'nom', 'prenom'
            ).first()
            if visible_head:
                head_name = visible_head.nom_complet

        for attr in ('chef_famille', 'nom_chef', 'chef', 'responsable', 'nom'):
            if head_name:
                break
            value = getattr(famille, attr, '')
            if value:
                head_name = str(value)
                break
        if not head_name:
            head_name = 'Non renseigne'

        household_id = ''
        for attr in ('household_id', 'code', 'numero_dossier', 'reference'):
            value = getattr(famille, attr, '')
            if value:
                household_id = str(value)
                break
        if not household_id:
            household_id = str(getattr(famille, 'id', ''))[:8].upper() or 'N/A'

        registration_date = None
        for attr in ('date_creation', 'created_at', 'date_enregistrement'):
            value = getattr(famille, attr, None)
            if value:
                registration_date = value
                break

        status_value = ''
        for attr in ('statut', 'status'):
            value = getattr(famille, attr, '')
            if value:
                status_value = str(value)
                break

        status_label = status_value.replace('_', ' ').title() if status_value else 'Active'
        status_classes = 'bg-green-100 text-green-700'
        if status_value in ('pending', 'en_attente'):
            status_classes = 'bg-amber-100 text-amber-700'
        elif status_value in ('inactive', 'archivee'):
            status_classes = 'bg-slate-200 text-slate-700'

        family_rows.append({
            'head_name': head_name,
            'household_id': household_id,
            'members_count': members_count,
            'registration_date': registration_date,
            'status_label': status_label,
            'status_classes': status_classes,
        })

    return family_rows


def _build_core_services(infrastructure_stats: list) -> list:
    stats_by_code = {item['code']: item for item in infrastructure_stats}
    service_defs = [
        {
            'label': 'Education',
            'type_codes': {'ecole', 'ecole_maternelle', 'lycee', 'universite'},
            'icon': 'school',
        },
        {
            'label': 'Sante',
            'type_codes': {'hopital', 'dispensaire', 'centre_sante'},
            'icon': 'medical_services',
        },
        {
            'label': 'Eau',
            'type_codes': {'puit', 'forage'},
            'icon': 'water_drop',
        },
        {
            'label': 'Electricite',
            'type_codes': {'electricite'},
            'icon': 'bolt',
        },
    ]

    core_services = []
    for service in service_defs:
        total = sum(
            stats_by_code[code]['count']
            for code in service['type_codes']
            if code in stats_by_code
        )
        core_services.append({
            'label': service['label'],
            'icon': service['icon'],
            'available': total > 0,
            'count': total,
        })

    return core_services


def _get_stats() -> dict:
    """
    Calcule toutes les statistiques pour les cards du dashboard.
    Utilise des agrégations SQL pour la performance.
    """
    villages_qs = Village.objects.filter(deleted__isnull=True)
    infras_qs   = Infrastructure.objects.filter(deleted__isnull=True)

    total_villages        = villages_qs.count()
    population_totale     = villages_qs.aggregate(
                                total=Sum('population_estimee')
                            )['total'] or 0
    total_infrastructures = infras_qs.count()

    # Pourcentage arbitraire pour la barre de progression
    pct_infras = min(int((total_infrastructures / (total_villages * 5)) * 100), 100) \
                 if total_villages else 0

    # Villages ayant au moins 1 école
    villages_avec_ecole = villages_qs.filter(
        infrastructures__type_infrastructure='ecole',
        infrastructures__deleted__isnull=True
    ).distinct().count()

    # Villages ayant au moins 1 structure de santé
    villages_avec_sante = villages_qs.filter(
        infrastructures__type_infrastructure__in=[
            'hopital', 'dispensaire', 'centre_sante'
        ],
        infrastructures__deleted__isnull=True
    ).distinct().count()

    # Villages ayant puits ou forage
    villages_avec_eau = villages_qs.filter(
        infrastructures__type_infrastructure__in=['puit', 'forage'],
        infrastructures__deleted__isnull=True
    ).distinct().count()

    # Villages ayant électricité
    villages_avec_electricite = villages_qs.filter(
        infrastructures__type_infrastructure='electricite',
        infrastructures__deleted__isnull=True
    ).distinct().count()

    # Familles (si l'app families est installée)
    try:
        from families.models import Family
        total_familles = Family.objects.filter(
            deleted__isnull=True
        ).count()
    except Exception:
        total_familles = 0

    return {
        'total_villages':            total_villages,
        'population_totale':         population_totale,
        'total_infrastructures':     total_infrastructures,
        'total_familles':            total_familles,
        'pct_infras':                pct_infras,
        'villages_avec_ecole':       villages_avec_ecole,
        'villages_avec_sante':       villages_avec_sante,
        'villages_avec_eau':         villages_avec_eau,
        'villages_avec_electricite': villages_avec_electricite,
    }


# ── Liste ─────────────────────────────────────────────────────

@method_decorator(login_required, name='dispatch')
class VillageListView(View):

    template_name = 'village/liste.html'

    def get(self, request):
        q        = request.GET.get('q', '').strip()
        page     = _safe_positive_int(request.GET.get('page', 1), 1)
        par_page = _safe_positive_int(request.GET.get('par_page', 10), 10)
        infra    = request.GET.get('infra', '').strip()
        pop      = request.GET.get('pop', '').strip()

        # ── Récupération via use case ────────────────────────
        use_case = ListVillagesUseCase(get_repo())
        result   = use_case.execute(q=q, page=page, par_page=par_page)

        # ── Filtre infra et pop (post-filtre sur les DTOs) ───
        # Pour les filtres avancés on repasse par l'ORM direct
        villages_qs = Village.objects.filter(deleted__isnull=True)

        if q:
            villages_qs = villages_qs.filter(nom__icontains=q)

        if infra:
            villages_qs = villages_qs.filter(
                infrastructures__type_infrastructure=infra,
                infrastructures__deleted__isnull=True
            ).distinct()

        if pop:
            try:
                villages_qs = villages_qs.filter(
                    population_estimee__gte=int(pop)
                )
            except ValueError:
                pass

        # Prefetch infrastructures pour éviter N+1 dans le template
        villages_qs = villages_qs.prefetch_related(
            'infrastructures'
        ).order_by('nom')

        # ── Stats cards ──────────────────────────────────────
        paginator = Paginator(villages_qs, par_page)
        page_obj = paginator.get_page(page)
        current_page = page_obj.number
        total = paginator.count
        display_start = ((current_page - 1) * par_page) + 1 if total else 0
        display_end = min(current_page * par_page, total) if total else 0
        stats = _get_stats()

        return render(request, self.template_name, {
            # Pour la table
            'villages':  page_obj.object_list,
            'q':         q,
            'infra':     infra,
            'pop':       pop,

            # Pour la pagination
            'result':    result,
            'page':      current_page,
            'nb_pages':  paginator.num_pages,
            'total':     total,
            'par_page':  par_page,
            'display_start': display_start,
            'display_end': display_end,

            # Pour les stats cards
            'stats': stats,
        })


# ── Détail ────────────────────────────────────────────────────

@method_decorator(login_required, name='dispatch')
class VillageDetailView(View):

    template_name = 'village/detail.html'

    def get(self, request, village_id):
        use_case = GetVillageUseCase(get_repo())
        village  = use_case.execute(str(village_id))

        if not village:
            messages.error(request, "Village introuvable.")
            return redirect('dashbord:village-list')

        # Données supplémentaires pour la page détail
        village_obj = Village.objects.prefetch_related('infrastructures').get(
            id=village_id,
            deleted__isnull=True,
        )
        infrastructures = list(
            village_obj.infrastructures.filter(deleted__isnull=True).order_by(
                'type_infrastructure', 'nom'
            )
        )
        infrastructure_stats = _build_infrastructure_type_stats(infrastructures)
        state_stats = _build_infrastructure_state_stats(infrastructures)
        core_services = _build_core_services(infrastructure_stats)
        available_core_services = sum(
            1 for item in core_services if item['available']
        )
        coverage_percent = int(
            round((available_core_services / len(core_services)) * 100)
        ) if core_services else 0
        familles_manager = village_obj._get_familles_manager()
        family_rows = _build_family_rows(familles_manager, request.user)
        infrastructure_rows = []

        for infra in infrastructures:
            ui_meta = _infra_ui_meta(infra.type_infrastructure)
            etat_meta = _etat_ui_meta(infra.etat)
            infrastructure_rows.append({
                'icon': ui_meta['icon'],
                'type_label': infra.get_type_infrastructure_display(),
                'name': infra.nom,
                'description': infra.description,
                'capacity': infra.capacite,
                'manager': infra.responsable,
                'contact': infra.contact_responsable,
                'built_at': infra.date_construction,
                'state_label': infra.get_etat_display(),
                'state_classes': etat_meta['badge_classes'],
                'badge_classes': ui_meta['badge_classes'],
            })

        return render(request, self.template_name, {
            'village':     village,       # DTO pour les données de base
            'village_obj': village_obj,   # Model pour les relations
            'infras_par_type': village_obj.get_infrastructures_by_type(),
            'infrastructure_stats': infrastructure_stats,
            'state_stats': state_stats,
            'highlight_infrastructures': infrastructure_stats[:4],
            'recent_infrastructures': _build_recent_infrastructure_rows(
                infrastructures
            ),
            'core_services': core_services,
            'available_core_services': available_core_services,
            'coverage_percent': coverage_percent,
            'family_rows': family_rows,
            'has_family_relation': familles_manager is not None,
            'infrastructure_rows': infrastructure_rows,
            'infrastructure_count': len(infrastructure_rows),
            'infrastructure_type_count': len(infrastructure_stats),
            **_map_service_context(),
        })


# ── Création ──────────────────────────────────────────────────

@method_decorator(login_required, name='dispatch')
class VillageCreateView(View):

    template_name = 'village/formulaire.html'

    def get(self, request):
        ensure_registry_management(request.user)
        return render(request, self.template_name, {
            'titre':  'Ajouter un village',
            'action': 'create',
            'infrastructure_type_options': _get_infrastructure_type_options(),
            'infrastructure_state_options': _get_infrastructure_state_options(),
            'infrastructure_form_rows': _build_infrastructure_form_rows(),
            **_map_service_context(),
        })

    def post(self, request):
        ensure_registry_management(request.user)
        data = CreateVillageDTO(
            nom=request.POST.get('nom', '').strip(),
            description=request.POST.get('description', '').strip(),
            latitude=self._float_or_none(request.POST.get('latitude')),
            longitude=self._float_or_none(request.POST.get('longitude')),
            population_estimee=_safe_int(
                request.POST.get('population_estimee', 0) or 0
            ),
            chef_village=request.POST.get('chef_village', '').strip(),
            created_by_id=str(request.user.id),
        )

        try:
            village = CreateVillageUseCase(get_repo()).execute(data)
            _sync_village_infrastructures(
                village.id,
                _normalize_infrastructure_form_rows(request.POST),
            )
            messages.success(
                request,
                f"Village « {village.nom} » créé avec succès."
            )
            return redirect('dashbord:village-detail', village_id=village.id)

        except VillageDejaExistantError as e:
            messages.error(request, str(e))
            return render(request, self.template_name, {
                'titre':     'Ajouter un village',
                'action':    'create',
                'form_data': request.POST,
                'infrastructure_type_options': _get_infrastructure_type_options(),
                'infrastructure_state_options': _get_infrastructure_state_options(),
                'infrastructure_form_rows': _build_infrastructure_form_rows(
                    post_data=request.POST
                ),
                **_map_service_context(),
            })

    @staticmethod
    def _float_or_none(value):
        try:
            return float(value) if value else None
        except (ValueError, TypeError):
            return None


# ── Modification ──────────────────────────────────────────────

@method_decorator(login_required, name='dispatch')
class VillageUpdateView(View):

    template_name = 'village/formulaire.html'

    def get(self, request, village_id):
        ensure_registry_management(request.user)
        village = GetVillageUseCase(get_repo()).execute(str(village_id))
        if not village:
            messages.error(request, "Village introuvable.")
            return redirect('dashbord:village-list')

        return render(request, self.template_name, {
            'titre':   f'Modifier — {village.nom}',
            'action':  'update',
            'village': village,
            'infrastructure_type_options': _get_infrastructure_type_options(),
            'infrastructure_state_options': _get_infrastructure_state_options(),
            'infrastructure_form_rows': _build_infrastructure_form_rows(
                village_id=village.id
            ),
            **_map_service_context(),
        })

    def post(self, request, village_id):
        ensure_registry_management(request.user)
        data = UpdateVillageDTO(
            id=str(village_id),
            nom=request.POST.get('nom', '').strip(),
            description=request.POST.get('description', '').strip(),
            latitude=VillageCreateView._float_or_none(
                request.POST.get('latitude')
            ),
            longitude=VillageCreateView._float_or_none(
                request.POST.get('longitude')
            ),
            population_estimee=_safe_int(
                request.POST.get('population_estimee', 0) or 0
            ),
            chef_village=request.POST.get('chef_village', '').strip(),
        )

        try:
            village = UpdateVillageUseCase(get_repo()).execute(data)
            _sync_village_infrastructures(
                village.id,
                _normalize_infrastructure_form_rows(request.POST),
            )
            messages.success(
                request,
                f"Village « {village.nom} » modifié avec succès."
            )
            return redirect(
                'dashbord:village-detail', village_id=village.id
            )

        except (VillageDejaExistantError, VillageIntrouvableError) as e:
            messages.error(request, str(e))
            return render(request, self.template_name, {
                'titre':     f'Modifier',
                'action':    'update',
                'form_data': request.POST,
                'infrastructure_type_options': _get_infrastructure_type_options(),
                'infrastructure_state_options': _get_infrastructure_state_options(),
                'infrastructure_form_rows': _build_infrastructure_form_rows(
                    post_data=request.POST
                ),
                **_map_service_context(),
            })


# ── Suppression ───────────────────────────────────────────────

@method_decorator(login_required, name='dispatch')
class VillageDeleteView(View):

    def post(self, request, village_id):
        ensure_registry_delete(request.user)
        try:
            DeleteVillageUseCase(get_repo()).execute(str(village_id))
            messages.success(request, "Village supprimé avec succès.")
        except VillageIntrouvableError as e:
            messages.error(request, str(e))

        return redirect('dashbord:village-list')
