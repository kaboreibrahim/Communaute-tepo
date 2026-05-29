# villages/repositories/django_village_repo.py
# Implémentation concrète avec Django ORM
# C'est ICI seulement qu'on touche aux models Django

from typing import Optional, List, Tuple
from django.core.paginator import Paginator
from ..models import Village, Infrastructure
from ..repositories.interfaces import VillageRepositoryInterface
from ..dtos.village_dto import (
    VillageDTO, InfrastructureDTO,
    CreateVillageDTO, UpdateVillageDTO,
    VillageListDTO,
)


QUICK_INFRASTRUCTURE_DEFAULTS = {
    type_code: type_label
    for type_code, type_label in Infrastructure.TYPES_INFRASTRUCTURE
}

AUTO_INFRA_DESCRIPTION = 'Cree automatiquement depuis le formulaire village.'


def _infra_to_dto(infra: Infrastructure) -> InfrastructureDTO:
    """Convertit un objet Infrastructure Django → DTO."""
    return InfrastructureDTO(
        id=str(infra.id),
        type_infrastructure=infra.type_infrastructure,
        type_label=infra.get_type_infrastructure_display(),
        nom=infra.nom,
        etat=infra.etat,
        etat_label=infra.get_etat_display(),
        capacite=infra.capacite,
        responsable=infra.responsable,
        contact_responsable=infra.contact_responsable,
    )


def _village_to_dto(
    village: Village,
    with_infras: bool = False
) -> VillageDTO:
    """Convertit un objet Village Django → DTO."""
    infras = []
    if with_infras:
        infras = [
            _infra_to_dto(i)
            for i in village.infrastructures.filter(deleted__isnull=True)
        ]
    return VillageDTO(
        id=str(village.id),
        nom=village.nom,
        description=village.description,
        latitude=village.latitude,
        longitude=village.longitude,
        population_estimee=village.population_estimee,
        chef_village=village.chef_village,
        date_creation=village.date_creation,
        nombre_familles=village.nombre_familles,
        nombre_habitants=village.nombre_habitants,
        nombre_infrastructures=village.nombre_total_infrastructures,
        infrastructures=infras,
    )


def _normalize_infrastructure_types(infrastructure_types: List[str]) -> List[str]:
    normalized = []
    seen = set()

    for type_code in infrastructure_types or []:
        if type_code not in QUICK_INFRASTRUCTURE_DEFAULTS or type_code in seen:
            continue
        normalized.append(type_code)
        seen.add(type_code)

    return normalized


def _sync_quick_infrastructures(village: Village, infrastructure_types: List[str]) -> None:
    selected_types = set(_normalize_infrastructure_types(infrastructure_types))
    existing_quick_infras = village.infrastructures.filter(
        deleted__isnull=True,
        type_infrastructure__in=QUICK_INFRASTRUCTURE_DEFAULTS.keys(),
    )

    existing_by_type = {}
    for infra in existing_quick_infras:
        existing_by_type.setdefault(infra.type_infrastructure, []).append(infra)

    for type_code in selected_types:
        if type_code in existing_by_type:
            continue
        Infrastructure.objects.create(
            village=village,
            type_infrastructure=type_code,
            nom=QUICK_INFRASTRUCTURE_DEFAULTS[type_code],
            description=AUTO_INFRA_DESCRIPTION,
        )

    for type_code, infrastructures in existing_by_type.items():
        if type_code in selected_types:
            continue
        for infra in infrastructures:
            if (
                infra.description == AUTO_INFRA_DESCRIPTION
                and infra.nom == QUICK_INFRASTRUCTURE_DEFAULTS[type_code]
            ):
                infra.delete()


class DjangoVillageRepository(VillageRepositoryInterface):

    def get_all(
        self,
        q: str = '',
        page: int = 1,
        par_page: int = 20
    ) -> Tuple[List[VillageDTO], int]:

        qs = Village.objects.filter(
            deleted__isnull=True   # SafeDelete
        ).order_by('nom')

        if q:
            qs = qs.filter(nom__icontains=q)

        total    = qs.count()
        paginator = Paginator(qs, par_page)
        page_obj  = paginator.get_page(page)

        dtos = [_village_to_dto(v) for v in page_obj]
        return dtos, total

    def get_by_id(self, village_id: str) -> Optional[VillageDTO]:
        try:
            village = Village.objects.get(
                id=village_id,
                deleted__isnull=True
            )
            return _village_to_dto(village, with_infras=True)
        except Village.DoesNotExist:
            return None

    def create(self, data: CreateVillageDTO) -> VillageDTO:
        village = Village.objects.create(
            nom=data.nom,
            description=data.description,
            latitude=data.latitude,
            longitude=data.longitude,
            population_estimee=data.population_estimee,
            chef_village=data.chef_village,
            created_by_id=data.created_by_id,
        )
        _sync_quick_infrastructures(village, data.infrastructure_types)
        return _village_to_dto(village)

    def update(self, data: UpdateVillageDTO) -> VillageDTO:
        village = Village.objects.get(
            id=data.id,
            deleted__isnull=True
        )
        village.nom                = data.nom
        village.description        = data.description
        village.latitude           = data.latitude
        village.longitude          = data.longitude
        village.population_estimee = data.population_estimee
        village.chef_village       = data.chef_village
        village.save()
        _sync_quick_infrastructures(village, data.infrastructure_types)
        return _village_to_dto(village)

    def delete(self, village_id: str) -> bool:
        try:
            village = Village.objects.get(
                id=village_id,
                deleted__isnull=True
            )
            village.delete()   # SafeDelete → soft delete
            return True
        except Village.DoesNotExist:
            return False

    def exists_by_nom(
        self, nom: str, exclude_id: str = None
    ) -> bool:
        qs = Village.objects.filter(
            nom__iexact=nom,
            deleted__isnull=True
        )
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
        return qs.exists()
