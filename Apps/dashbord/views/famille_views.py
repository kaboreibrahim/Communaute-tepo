import json
from types import SimpleNamespace

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from Apps.families.dtos.family_dto import CreateFamilyDTO, UpdateFamilyDTO
from Apps.families.models import Family
from Apps.families.repositories.django_family_repo import DjangoFamilyRepository
from Apps.families.use_cases.create_family import (
    CreateFamilyUseCase,
    FamilyDejaExistanteError as CreateFamilyDejaExistanteError,
)
from Apps.families.use_cases.delete_family import (
    DeleteFamilyUseCase,
    FamilyIntrouvableError as DeleteFamilyIntrouvableError,
)
from Apps.families.use_cases.get_family import GetFamilyUseCase
from Apps.families.use_cases.list_families import ListFamiliesUseCase
from Apps.families.use_cases.update_family import (
    FamilyDejaExistanteError as UpdateFamilyDejaExistanteError,
    FamilyIntrouvableError as UpdateFamilyIntrouvableError,
    UpdateFamilyUseCase,
)
from Apps.person.models import Person
from Apps.person.repositories.django_person_repo import DjangoPersonRepository
from Apps.person.use_cases.get_person import GetFamilyTreeUseCase
from Apps.villages.models import Village
from Apps.dashbord.security import (
    ensure_registry_delete,
    ensure_registry_management,
    filter_person_queryset_for_user,
    is_limited_data_entry_agent,
)


def family_repo():
    return DjangoFamilyRepository()


def person_repo():
    return DjangoPersonRepository()


def _get_villages():
    return Village.objects.filter(deleted__isnull=True).order_by("nom")


def _empty_famille():
    return SimpleNamespace(
        id="",
        nom_famille="",
        village_id="",
        village_nom="",
        description="",
        chef_nom="",
        nombre_membres=0,
        date_maj=None,
    )


def _tree_to_dict(node) -> dict:
    if not node:
        return {}
    return {
        "id": node.id,
        "nom_complet": node.nom_complet,
        "prenom": node.prenom,
        "nom": node.nom,
        "genre": node.genre,
        "age": node.age,
        "est_vivant": node.est_vivant,
        "photo": node.photo,
        "conjoint": node.conjoint,
        "generation": node.generation,
        "date_naissance": node.date_naissance.isoformat() if node.date_naissance else None,
        "date_deces": node.date_deces.isoformat() if node.date_deces else None,
        "residence_label": node.residence_label,
        "lieu_residence": node.lieu_residence,
        "nombre_enfants": len(node.enfants),
        "enfants": [_tree_to_dict(enfant) for enfant in node.enfants],
    }


def _count_tree_nodes(node) -> int:
    if not node:
        return 0
    return 1 + sum(_count_tree_nodes(enfant) for enfant in node.enfants)


def _tree_depth(node) -> int:
    if not node:
        return 0
    if not node.enfants:
        return 1
    return 1 + max(_tree_depth(enfant) for enfant in node.enfants)


@method_decorator(login_required, name="dispatch")
class FamilyListView(View):
    template_name = "famille/liste.html"

    def get(self, request):
        q = request.GET.get("q", "").strip()
        village_id = request.GET.get("village", "").strip()
        residence = request.GET.get("residence", "").strip()
        page = int(request.GET.get("page", 1))
        par_page = int(request.GET.get("par_page", 20))
        residence_choices = Person.RESIDENCE_CHOICES
        allowed_residences = {value for value, _ in residence_choices}

        if residence not in allowed_residences:
            residence = ""

        result = ListFamiliesUseCase(family_repo()).execute(
            q=q,
            village_id=village_id,
            residence=residence,
            page=page,
            par_page=par_page,
        )

        families_qs = Family.objects.filter(deleted__isnull=True)
        persons_qs = filter_person_queryset_for_user(
            Person.objects.filter(deleted__isnull=True),
            request.user,
        )
        visible_persons_by_family = {}
        if is_limited_data_entry_agent(request.user):
            visible_people = persons_qs.select_related('famille').order_by(
                'famille_id', '-est_chef_famille', 'date_creation', 'nom', 'prenom'
            )
            for person in visible_people:
                visible_persons_by_family.setdefault(str(person.famille_id), person)

            for family_row in result.familles:
                visible_person = visible_persons_by_family.get(str(family_row.id))
                family_row.chef_nom = (
                    visible_person.nom_complet if visible_person else None
                )
                family_row.nombre_membres = persons_qs.filter(
                    famille_id=family_row.id
                ).count()

        total_familles = families_qs.count()
        total_personnes = persons_qs.count()
        familles_verifiees = (
            persons_qs.filter(
                est_chef_famille=True,
            )
            .values("famille_id")
            .distinct()
            .count()
        )
        taux_verifie = round(
            (familles_verifiees / total_familles) * 100, 1
        ) if total_familles else 0
        taille_moyenne = round(
            total_personnes / total_familles, 1
        ) if total_familles else 0
        display_start = ((page - 1) * par_page) + 1 if result.total else 0
        display_end = min(page * par_page, result.total) if result.total else 0
        pagination_start = max(1, page - 2)
        pagination_end = min(result.nb_pages, page + 2)

        stats = {
            "total_familles": total_familles,
            "total_personnes": total_personnes,
            "total_vivants": persons_qs.filter(
                est_vivant=True,
            ).count(),
            "total_diaspora": persons_qs.filter(
                type_residence="diaspora",
            ).count(),
            "familles_verifiees": familles_verifiees,
            "taux_verifie": taux_verifie,
            "taille_moyenne": taille_moyenne,
        }

        return render(
            request,
            self.template_name,
            {
                "familles": result.familles,
                "result": result,
                "q": q,
                "village_id": village_id,
                "residence": residence,
                "residence_choices": residence_choices,
                "page": result.page,
                "nb_pages": result.nb_pages,
                "total": result.total,
                "par_page": par_page,
                "villages": _get_villages(),
                "stats": stats,
                "display_start": display_start,
                "display_end": display_end,
                "pagination_range": range(pagination_start, pagination_end + 1),
            },
        )


@method_decorator(login_required, name="dispatch")
class FamilyDetailView(View):
    template_name = "famille/detail.html"

    def get(self, request, family_id):
        famille = GetFamilyUseCase(family_repo()).execute(str(family_id))
        if not famille:
            messages.error(request, "Famille introuvable.")
            return redirect("dashbord:family-list")

        visible_members_qs = filter_person_queryset_for_user(
            Person.objects.filter(
                famille_id=family_id,
                deleted__isnull=True,
            ),
            request.user,
        )
        visible_member_ids = {
            str(person_id)
            for person_id in visible_members_qs.values_list('id', flat=True)
        }

        arbre = GetFamilyTreeUseCase(person_repo()).execute(str(family_id))
        if is_limited_data_entry_agent(request.user):
            famille.membres = [
                membre for membre in famille.membres
                if str(membre.id) in visible_member_ids
            ]
            if str(famille.chef_id or '') not in visible_member_ids:
                famille.chef_id = None
                famille.chef_nom = None
                arbre = None

        arbre_json = json.dumps(_tree_to_dict(arbre), ensure_ascii=False) if arbre else "{}"
        membres_qs = visible_members_qs
        detail_stats = {
            "total_membres": membres_qs.count(),
            "total_vivants": membres_qs.filter(est_vivant=True).count(),
            "total_diaspora": membres_qs.filter(type_residence="diaspora").count(),
            "total_village": membres_qs.filter(type_residence="village").count(),
            "total_ci": membres_qs.filter(type_residence="ci").count(),
            "profondeur": _tree_depth(arbre),
            "noeuds_arbre": _count_tree_nodes(arbre),
        }

        return render(
            request,
            self.template_name,
            {
                "famille": famille,
                "arbre_json": arbre_json,
                "detail_stats": detail_stats,
            },
        )


@method_decorator(login_required, name="dispatch")
class FamilyCreateView(View):
    template_name = "famille/family_form.html"

    def get(self, request):
        ensure_registry_management(request.user)
        return render(
            request,
            self.template_name,
            {
                "titre": "Ajouter une famille",
                "action": "create",
                "famille": _empty_famille(),
                "form_data": {},
                "villages": _get_villages(),
            },
        )

    def post(self, request):
        ensure_registry_management(request.user)
        data = CreateFamilyDTO(
            nom_famille=request.POST.get("nom_famille", "").strip(),
            village_id=request.POST.get("village_id", "").strip(),
            description=request.POST.get("description", "").strip(),
            created_by_id=str(request.user.id),
        )
        try:
            famille = CreateFamilyUseCase(family_repo()).execute(data)
            messages.success(
                request,
                f"Famille « {famille.nom_famille} » creee avec succes.",
            )
            return redirect("dashbord:family-detail", family_id=famille.id)
        except (CreateFamilyDejaExistanteError, ValueError) as exc:
            messages.error(request, str(exc))
            return render(
                request,
                self.template_name,
                {
                    "titre": "Ajouter une famille",
                    "action": "create",
                    "famille": _empty_famille(),
                    "villages": _get_villages(),
                    "form_data": request.POST,
                },
            )


@method_decorator(login_required, name="dispatch")
class FamilyUpdateView(View):
    template_name = "famille/family_form.html"

    def get(self, request, family_id):
        ensure_registry_management(request.user)
        famille = GetFamilyUseCase(family_repo()).execute(str(family_id))
        if not famille:
            messages.error(request, "Famille introuvable.")
            return redirect("dashbord:family-list")

        return render(
            request,
            self.template_name,
            {
                "titre": f"Modifier - {famille.nom_famille}",
                "action": "update",
                "famille": famille,
                "villages": _get_villages(),
            },
        )

    def post(self, request, family_id):
        ensure_registry_management(request.user)
        data = UpdateFamilyDTO(
            id=str(family_id),
            nom_famille=request.POST.get("nom_famille", "").strip(),
            village_id=request.POST.get("village_id", "").strip(),
            description=request.POST.get("description", "").strip(),
        )
        try:
            famille = UpdateFamilyUseCase(family_repo()).execute(data)
            messages.success(
                request,
                f"Famille « {famille.nom_famille} » modifiee.",
            )
            return redirect("dashbord:family-detail", family_id=famille.id)
        except UpdateFamilyIntrouvableError as exc:
            messages.error(request, str(exc))
            return redirect("dashbord:family-list")
        except UpdateFamilyDejaExistanteError as exc:
            messages.error(request, str(exc))
            famille = GetFamilyUseCase(family_repo()).execute(str(family_id))
            return render(
                request,
                self.template_name,
                {
                    "titre": f"Modifier - {(famille.nom_famille if famille else data.nom_famille) or 'Famille'}",
                    "action": "update",
                    "famille": famille,
                    "villages": _get_villages(),
                    "form_data": request.POST,
                },
            )


@method_decorator(login_required, name="dispatch")
class FamilyDeleteView(View):
    def post(self, request, family_id):
        ensure_registry_delete(request.user)
        try:
            DeleteFamilyUseCase(family_repo()).execute(str(family_id))
            messages.success(request, "Famille supprimee avec succes.")
        except DeleteFamilyIntrouvableError as exc:
            messages.error(request, str(exc))
        return redirect("dashbord:family-list")
