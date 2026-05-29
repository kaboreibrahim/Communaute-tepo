# villages/use_cases/list_villages.py

from ..repositories.interfaces import VillageRepositoryInterface
from ..dtos.village_dto import VillageListDTO
from math import ceil


class ListVillagesUseCase:

    def __init__(self, repository: VillageRepositoryInterface):
        self.repository = repository

    def execute(
        self, q: str = '', page: int = 1, par_page: int = 20
    ) -> VillageListDTO:

        villages, total = self.repository.get_all(
            q=q, page=page, par_page=par_page
        )
        return VillageListDTO(
            villages=villages,
            total=total,
            page=page,
            par_page=par_page,
            nb_pages=ceil(total / par_page) if par_page else 1,
            q=q,
        )