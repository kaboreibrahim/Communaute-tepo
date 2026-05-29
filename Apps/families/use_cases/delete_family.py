from math    import ceil
from typing  import Optional, List
 


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
 

 

class DeleteFamilyUseCase:
    """
    Soft-delete une famille.
    SafeDelete cascade vers les membres automatiquement.
    """
 
    def __init__(self, repo: FamilyRepositoryInterface):
        self.repo = repo
 
    def execute(self, family_id: str) -> bool:
        existante = self.repo.get_by_id(family_id)
        if not existante:
            raise FamilyIntrouvableError(
                f"Famille {family_id} introuvable."
            )
        return self.repo.delete(family_id)