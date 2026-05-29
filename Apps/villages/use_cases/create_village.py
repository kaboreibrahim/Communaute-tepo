# villages/use_cases/create_village.py

from ..repositories.interfaces import VillageRepositoryInterface
from ..dtos.village_dto import CreateVillageDTO, VillageDTO


class VillageDejaExistantError(Exception):
    """Levée si un village avec ce nom existe déjà."""
    pass


class CreateVillageUseCase:

    def __init__(self, repository: VillageRepositoryInterface):
        self.repository = repository

    def execute(self, data: CreateVillageDTO) -> VillageDTO:

        # Règle métier : nom unique dans Olodio
        if self.repository.exists_by_nom(data.nom):
            raise VillageDejaExistantError(
                f"Un village nommé '{data.nom}' existe déjà."
            )

        return self.repository.create(data)