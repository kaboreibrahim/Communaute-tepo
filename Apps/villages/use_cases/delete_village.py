# villages/use_cases/delete_village.py

from ..repositories.interfaces import VillageRepositoryInterface
from .update_village import VillageIntrouvableError


class DeleteVillageUseCase:

    def __init__(self, repository: VillageRepositoryInterface):
        self.repository = repository

    def execute(self, village_id: str) -> bool:
        existant = self.repository.get_by_id(village_id)
        if not existant:
            raise VillageIntrouvableError(
                f"Village {village_id} introuvable."
            )
        return self.repository.delete(village_id)