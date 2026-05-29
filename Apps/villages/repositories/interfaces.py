# villages/repositories/interfaces.py
# Contrat abstrait — indépendant de Django ORM
# Les use cases ne connaissent que cette interface

from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
from ..dtos.village_dto import (
    VillageDTO, CreateVillageDTO, UpdateVillageDTO
)


class VillageRepositoryInterface(ABC):

    @abstractmethod
    def get_all(
        self,
        q: str = '',
        page: int = 1,
        par_page: int = 20
    ) -> Tuple[List[VillageDTO], int]:
        """
        Retourne (liste de VillageDTO, total).
        q = filtre par nom.
        """
        ...

    @abstractmethod
    def get_by_id(self, village_id: str) -> Optional[VillageDTO]:
        """Retourne un VillageDTO ou None si introuvable."""
        ...

    @abstractmethod
    def create(self, data: CreateVillageDTO) -> VillageDTO:
        """Crée un village et retourne le DTO créé."""
        ...

    @abstractmethod
    def update(self, data: UpdateVillageDTO) -> VillageDTO:
        """Modifie un village et retourne le DTO mis à jour."""
        ...

    @abstractmethod
    def delete(self, village_id: str) -> bool:
        """Soft-delete un village. Retourne True si succès."""
        ...

    @abstractmethod
    def exists_by_nom(
        self, nom: str, exclude_id: str = None
    ) -> bool:
        """Vérifie si un village avec ce nom existe déjà."""
        ...