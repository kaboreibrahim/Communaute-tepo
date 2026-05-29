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
 
 
 
 
 
class DeletePersonUseCase:
    """Soft-delete une personne."""
 
    def __init__(self, repo: PersonRepositoryInterface):
        self.repo = repo
 
    def execute(self, person_id: str) -> bool:
        existante = self.repo.get_by_id(person_id)
        if not existante:
            raise PersonIntrouvableError(
                f"Personne {person_id} introuvable."
            )
        return self.repo.delete(person_id)
  