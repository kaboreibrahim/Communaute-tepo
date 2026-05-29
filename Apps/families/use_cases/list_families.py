from math    import ceil
from typing  import Optional, List
 
from Apps.families.dtos.family_dto import (
     FamilyListDTO,
  
    
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
 
class ListFamiliesUseCase:
    """
    Liste paginée des familles avec filtres.
    Utilisé par : dashboard/villages/liste_familles.html
    """
 
    def __init__(self, repo: FamilyRepositoryInterface):
        self.repo = repo
 
    def execute(
        self,
        q:          str = '',
        village_id: str = '',
        residence:  str = '',
        page:       int = 1,
        par_page:   int = 20,
    ) -> FamilyListDTO:
        familles, total = self.repo.get_all(
            q=q,
            village_id=village_id,
            residence=residence,
            page=page, par_page=par_page
        )
        return FamilyListDTO(
            familles=familles,
            total=total,
            page=page,
            par_page=par_page,
            nb_pages=ceil(total / par_page) if par_page else 1,
            q=q,
        )
 
 
 
