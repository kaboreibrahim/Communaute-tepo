from math    import ceil
from typing  import Optional, List
 
from Apps.families.dtos.family_dto import (
    FamilyDTO,
    CreateFamilyDTO
    
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
 

# ══════════════════════════════════════════════════════════════
# USE CASES — FAMILY
# ══════════════════════════════════════════════════════════════
 

 
class CreateFamilyUseCase:
    """
    Crée une nouvelle famille.
    Règle métier : nom unique par village.
    """
 
    def __init__(self, repo: FamilyRepositoryInterface):
        self.repo = repo
 
    def execute(self, data: CreateFamilyDTO) -> FamilyDTO:
        if not data.nom_famille.strip():
            raise ValueError("Le nom de famille est obligatoire.")
 
        if not data.village_id:
            raise ValueError("Le village est obligatoire.")
 
        # Règle : pas 2 familles du même nom dans le même village
        if self.repo.exists_by_nom_village(
            data.nom_famille, data.village_id
        ):
            raise FamilyDejaExistanteError(
                f"La famille « {data.nom_famille} » existe déjà "
                f"dans ce village."
            )
 
        return self.repo.create(data)
 
