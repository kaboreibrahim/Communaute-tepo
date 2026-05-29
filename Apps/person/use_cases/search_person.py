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
 
 
 
class SearchPersonUseCase:
    """
    Autocomplétion AJAX pour les champs père/mère.
    Retourne max 15 résultats filtrés par genre et village.
    """
 
    def __init__(self, repo: PersonRepositoryInterface):
        self.repo = repo
    
    def execute(
        self,
        q:          str,
        genre:      str = '',
        village_id: str = '',
        created_by_id: str = '',
        limit:      int = 15,
    ) -> List[PersonSearchResultDTO]:
        return self.repo.search_autocomplete(
            q=q, genre=genre, village_id=village_id,
            created_by_id=created_by_id, limit=limit
        )
 
 
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
