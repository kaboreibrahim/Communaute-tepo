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

from Apps.person.models import Person
 
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
 

class GetPersonUseCase:
    """Détail complet d'une personne avec ses relations."""
 
    def __init__(self, repo: PersonRepositoryInterface):
        self.repo = repo
 
    def execute(
        self, person_id: str, created_by_id: str = ''
    ) -> Optional[PersonDTO]:
        return self.repo.get_by_id(person_id, created_by_id=created_by_id)
 

 

 
 
class GetFamilyTreeUseCase:
    """
    Génère l'arbre généalogique d'une famille
    à partir du chef (personne sans père ni mère connu).
    """
 
    def __init__(self, repo: PersonRepositoryInterface):
        self.repo = repo
 
    def execute(
        self,
        family_id:      str,
        profondeur_max: int = 6,
    ) -> Optional[TreeNodeDTO]:
        # Trouver le chef : membre sans père ni mère
        
        chef = Person.objects.filter(
            est_chef_famille=True,
            famille_id=family_id,
            deleted__isnull=True,
        ).order_by('date_creation', 'nom', 'prenom').first()
 
        if not chef:
            return None
 
        return self.repo.build_tree(
            str(chef.id), profondeur_max=profondeur_max
        )
