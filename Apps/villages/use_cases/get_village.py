# villages/use_cases/get_village.py

from ..repositories.interfaces import VillageRepositoryInterface
from ..dtos.village_dto import VillageDTO
from typing import Optional


class GetVillageUseCase:

    def __init__(self, repository: VillageRepositoryInterface):
        self.repository = repository

    def execute(self, village_id: str) -> Optional[VillageDTO]:
        return self.repository.get_by_id(village_id)