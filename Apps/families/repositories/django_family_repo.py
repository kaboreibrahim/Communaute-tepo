from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from django.core.paginator import Paginator
from django.db.models import Q

from Apps.families.dtos.family_dto import (
    CreateFamilyDTO,
    FamilyDTO,
    FamilyLightDTO,
    UpdateFamilyDTO,
)
from Apps.families.models import Family
from Apps.person.dtos.person_dto import PersonLightDTO


class FamilyRepositoryInterface(ABC):
    @abstractmethod
    def get_all(
        self,
        q: str = "",
        village_id: str = "",
        residence: str = "",
        page: int = 1,
        par_page: int = 20,
    ) -> Tuple[List[FamilyLightDTO], int]: ...

    @abstractmethod
    def get_by_id(self, family_id: str) -> Optional[FamilyDTO]: ...

    @abstractmethod
    def create(self, data: CreateFamilyDTO) -> FamilyDTO: ...

    @abstractmethod
    def update(self, data: UpdateFamilyDTO) -> FamilyDTO: ...

    @abstractmethod
    def delete(self, family_id: str) -> bool: ...

    @abstractmethod
    def exists_by_nom_village(
        self, nom: str, village_id: str, exclude_id: str = None
    ) -> bool: ...


def _person_to_light(person) -> PersonLightDTO:
    return PersonLightDTO(
        id=str(person.id),
        code=person.code,
        nom=person.nom,
        prenom=person.prenom,
        nom_complet=person.nom_complet,
        genre=person.genre,
        genre_label=person.get_genre_display(),
        age=person.age,
        village=person.famille.village.nom if person.famille_id else "",
        famille_id=str(person.famille_id) if person.famille_id else "",
        famille_nom=person.famille.nom_famille if person.famille_id else "",
        est_vivant=person.est_vivant,
        photo=person.photo.url if person.photo else None,
    )


def _family_to_light(family) -> FamilyLightDTO:
    chef = family.chef
    return FamilyLightDTO(
        id=str(family.id),
        nom_famille=family.nom_famille,
        village_nom=family.village.nom,
        nombre_membres=family.membres.count(),
        chef_nom=chef.nom_complet if chef else None,
        date_creation=family.date_creation,
    )


def _family_to_dto(family, with_membres: bool = False) -> FamilyDTO:
    chef = family.chef
    membres = []
    if with_membres:
        membres = [_person_to_light(person) for person in family.membres.all()]

    return FamilyDTO(
        id=str(family.id),
        nom_famille=family.nom_famille,
        village_id=str(family.village_id),
        village_nom=family.village.nom,
        description=family.description or "",
        date_creation=family.date_creation,
        date_maj=family.date_maj,
        nombre_membres=family.membres.count(),
        chef_nom=chef.nom_complet if chef else None,
        chef_id=str(chef.id) if chef else None,
        membres=membres,
    )


class DjangoFamilyRepository(FamilyRepositoryInterface):
    def _qs(self):
        return Family.objects.filter(deleted__isnull=True)

    def get_all(
        self,
        q: str = "",
        village_id: str = "",
        residence: str = "",
        page: int = 1,
        par_page: int = 20,
    ) -> Tuple[List[FamilyLightDTO], int]:
        qs = self._qs().select_related("village").order_by("nom_famille")
        use_distinct = False
        if q:
            qs = qs.filter(
                Q(nom_famille__icontains=q)
                | Q(village__nom__icontains=q)
                | Q(membres__deleted__isnull=True, membres__nom__icontains=q)
                | Q(membres__deleted__isnull=True, membres__prenom__icontains=q)
            )
            use_distinct = True
        if village_id:
            qs = qs.filter(village_id=village_id)
        if residence:
            qs = qs.filter(
                membres__deleted__isnull=True,
                membres__type_residence=residence,
            )
            use_distinct = True
        if use_distinct:
            qs = qs.distinct()

        total = qs.count()
        page_obj = Paginator(qs, par_page).get_page(page)
        return [_family_to_light(family) for family in page_obj], total

    def get_by_id(self, family_id: str) -> Optional[FamilyDTO]:
        try:
            family = Family.objects.select_related("village").prefetch_related(
                "membres__famille__village",
                "membres__pere",
                "membres__mere",
            ).get(id=family_id, deleted__isnull=True)
            return _family_to_dto(family, with_membres=True)
        except Exception:
            return None

    def create(self, data: CreateFamilyDTO) -> FamilyDTO:
        family = Family.objects.create(
            nom_famille=data.nom_famille,
            village_id=data.village_id,
            description=data.description,
            created_by_id=data.created_by_id,
        )
        return _family_to_dto(family)

    def update(self, data: UpdateFamilyDTO) -> FamilyDTO:
        family = Family.objects.get(id=data.id, deleted__isnull=True)
        family.nom_famille = data.nom_famille
        family.village_id = data.village_id
        family.description = data.description
        family.save()
        return _family_to_dto(family)

    def delete(self, family_id: str) -> bool:
        try:
            family = Family.objects.get(id=family_id, deleted__isnull=True)
            family.delete()
            return True
        except Exception:
            return False

    def exists_by_nom_village(
        self, nom: str, village_id: str, exclude_id: str = None
    ) -> bool:
        qs = Family.objects.filter(
            nom_famille__iexact=nom,
            village_id=village_id,
            deleted__isnull=True,
        )
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
        return qs.exists()
