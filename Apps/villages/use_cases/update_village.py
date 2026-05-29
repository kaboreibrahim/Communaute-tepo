# villages/use_cases/update_village.py

from ..repositories.interfaces import VillageRepositoryInterface
from ..dtos.village_dto import UpdateVillageDTO, VillageDTO
from .create_village import VillageDejaExistantError


class VillageIntrouvableError(Exception):
    pass


class UpdateVillageUseCase:

    def __init__(self, repository: VillageRepositoryInterface):
        self.repository = repository

    def execute(self, data: UpdateVillageDTO) -> VillageDTO:

        # Vérifier que le village existe
        existant = self.repository.get_by_id(data.id)
        if not existant:
            raise VillageIntrouvableError(
                f"Village {data.id} introuvable."
            )

        # Règle métier : nom unique (sauf lui-même)
        if self.repository.exists_by_nom(data.nom, exclude_id=data.id):
            raise VillageDejaExistantError(
                f"Un autre village nommé '{data.nom}' existe déjà."
            )

        return self.repository.update(data)