from math    import ceil
from typing  import Optional, List
 
from Apps.families.dtos.family_dto import (
    FamilyDTO, UpdateFamilyDTO,
    
)

from Apps.families.repositories.django_family_repo import (
    FamilyRepositoryInterface,
    
)


 
# ══════════════════════════════════════════════════════════════
# EXCEPTIONS MÉTIER
# ══════════════════════════════════════════════════════════════
 
class FamilyDejaExistanteError(Exception):
    """Famille avec ce nom déjà existante dans ce village."""
 
class FamilyIntrouvableError(Exception):
    """Famille introuvable ou supprimée."""
 
class PersonIntrouvableError(Exception):
    """Personne introuvable ou supprimée."""
 
class PersonGenreInvalideError(Exception):
    """Genre incompatible (ex: père doit être M)."""
 
class FamilleObligatoireError(Exception):
    """La famille est obligatoire pour créer une personne."""
 

class UpdateFamilyUseCase:
    """
    Modifie une famille existante.
    Règle : nom unique par village (sauf lui-même).
    """
 
    def __init__(self, repo: FamilyRepositoryInterface):
        self.repo = repo
 
    def execute(self, data: UpdateFamilyDTO) -> FamilyDTO:
        existante = self.repo.get_by_id(data.id)
        if not existante:
            raise FamilyIntrouvableError(
                f"Famille {data.id} introuvable."
            )
 
        if self.repo.exists_by_nom_village(
            data.nom_famille, data.village_id, exclude_id=data.id
        ):
            raise FamilyDejaExistanteError(
                f"Une autre famille « {data.nom_famille} » "
                f"existe déjà dans ce village."
            )
 
        return self.repo.update(data)
 
 
 
