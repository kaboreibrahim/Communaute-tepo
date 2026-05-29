from math    import ceil
from typing  import Optional, List
 
from Apps.person.dtos.person_dto import (
    PersonDTO, PersonLightDTO,
    CreatePersonDTO, UpdatePersonDTO,
    TreeNodeDTO, PersonSearchResultDTO,
)
from Apps.person.repositories.django_person_repo import (
    PersonRepositoryInterface,
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
# USE CASES — PERSON
# ══════════════════════════════════════════════════════════════
 
class ListPersonsUseCase:
    """
    Liste paginée des personnes avec filtres multiples.
    Utilisé par : dashboard/familles/liste_personnes.html
    """
 
    def __init__(self, repo: PersonRepositoryInterface):
        self.repo = repo
 
    def execute(
        self,
        q:          str = '',
        famille_id: str = '',
        genre:      str = '',
        village_id: str = '',
        created_by_id: str = '',
        page:       int = 1,
        par_page:   int = 20,
    ) -> dict:
        personnes, total = self.repo.get_all(
            q=q, famille_id=famille_id, genre=genre,
            village_id=village_id, created_by_id=created_by_id,
            page=page, par_page=par_page
        )
        return {
            'personnes': personnes,
            'total':     total,
            'page':      page,
            'par_page':  par_page,
            'nb_pages':  ceil(total / par_page) if par_page else 1,
            'q':         q,
        }
 
  
