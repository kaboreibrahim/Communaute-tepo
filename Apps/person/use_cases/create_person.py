from Apps.person.dtos.person_dto import PersonDTO, CreatePersonDTO
from Apps.person.repositories.django_person_repo import (
    PersonRepositoryInterface,
)
from Apps.families.repositories.django_family_repo import (
    FamilyRepositoryInterface,
)
from Apps.person.models import Person


class FamilyDejaExistanteError(Exception):
    """Famille avec ce nom deja existante dans ce village."""


class FamilyIntrouvableError(Exception):
    """Famille introuvable ou supprimee."""


class PersonIntrouvableError(Exception):
    """Personne introuvable ou supprimee."""


class PersonGenreInvalideError(Exception):
    """Genre incompatible (ex: pere doit etre M)."""


class FamilleObligatoireError(Exception):
    """La famille est obligatoire pour creer une personne."""


class ConjointIndisponibleError(Exception):
    """Conjoint deja attribue ou relation invalide."""


class ChefFamilleDejaDefiniError(Exception):
    """Un chef de famille existe deja pour cette famille."""


class CreatePersonUseCase:
    """
    Cree une nouvelle personne.
    Regles metier :
      - famille obligatoire
      - pere doit etre genre M
      - mere doit etre genre F
      - pere / mere / conjoint peuvent aussi etre saisis librement
    """

    def __init__(
        self,
        person_repo: PersonRepositoryInterface,
        family_repo: FamilyRepositoryInterface,
    ):
        self.person_repo = person_repo
        self.family_repo = family_repo

    def execute(self, data: CreatePersonDTO) -> PersonDTO:
        data.pere_nom_libre = (data.pere_nom_libre or '').strip()
        data.mere_nom_libre = (data.mere_nom_libre or '').strip()
        data.conjoint_nom_libre = (data.conjoint_nom_libre or '').strip()

        if data.pere_nom_libre:
            data.pere_id = None

        if data.mere_nom_libre:
            data.mere_id = None

        if data.conjoint_nom_libre:
            data.conjoint_id = None

        if not data.famille_id:
            raise FamilleObligatoireError(
                "La famille est obligatoire."
            )

        famille = self.family_repo.get_by_id(data.famille_id)
        if not famille:
            raise FamilyIntrouvableError(
                f"Famille {data.famille_id} introuvable."
            )

        if data.est_chef_famille:
            chef_existant = Person.objects.filter(
                famille_id=data.famille_id,
                est_chef_famille=True,
                deleted__isnull=True,
            ).first()
            if chef_existant:
                raise ChefFamilleDejaDefiniError(
                    f"{chef_existant.nom_complet} est deja defini(e) comme chef de cette famille."
                )

        if data.pere_id:
            pere = self.person_repo.get_by_id(data.pere_id)
            if pere and pere.genre != 'M':
                raise PersonGenreInvalideError(
                    "Le père doit être de genre Masculin."
                )

        if data.mere_id:
            mere = self.person_repo.get_by_id(data.mere_id)
            if mere and mere.genre != 'F':
                raise PersonGenreInvalideError(
                    "La mère doit être de genre Féminin."
                )

        if data.conjoint_id:
            conjoint = self.person_repo.get_by_id(data.conjoint_id)
            if not conjoint:
                raise ConjointIndisponibleError(
                    "Le conjoint sélectionné est introuvable."
                )

            deja_reference = Person.objects.filter(
                conjoint_id=data.conjoint_id,
                deleted__isnull=True,
            ).first()
            if deja_reference:
                raise ConjointIndisponibleError(
                    f"{conjoint.nom_complet} est déjà défini(e) comme conjoint(e) de {deja_reference.nom_complet}."
                )

            if conjoint.conjoint_id:
                partenaire = self.person_repo.get_by_id(conjoint.conjoint_id)
                partenaire_nom = (
                    partenaire.nom_complet if partenaire else "une autre personne"
                )
                raise ConjointIndisponibleError(
                    f"{conjoint.nom_complet} est déjà lié(e) à {partenaire_nom}."
                )

        return self.person_repo.create(data)
