from django.test import TestCase

from Apps.families.models import Family
from Apps.families.repositories.django_family_repo import DjangoFamilyRepository
from Apps.person.dtos.person_dto import CreatePersonDTO, UpdatePersonDTO
from Apps.person.models import Person
from Apps.person.repositories.django_person_repo import DjangoPersonRepository
from Apps.person.use_cases.create_person import (
    ChefFamilleDejaDefiniError as CreateChefFamilleDejaDefiniError,
    CreatePersonUseCase,
)
from Apps.person.use_cases.update_person import (
    ChefFamilleDejaDefiniError as UpdateChefFamilleDejaDefiniError,
    ConjointIndisponibleError,
    UpdatePersonUseCase,
)
from Apps.villages.models import Village


class PersonCodeTests(TestCase):
    def setUp(self):
        self.village = Village.objects.create(nom="Olodio")
        self.family = Family.objects.create(
            nom_famille="Bakayoko",
            village=self.village,
        )

    def test_code_is_generated_automatically_and_stays_unique(self):
        first_person = Person.objects.create(
            nom="Bakayoko",
            prenom="Abdoulaye",
            genre="M",
            famille=self.family,
        )
        second_person = Person.objects.create(
            nom="Bakayoko",
            prenom="Adama",
            genre="F",
            famille=self.family,
        )

        self.assertEqual(first_person.code, "BAKAYOKO-0001")
        self.assertEqual(second_person.code, "BAKAYOKO-0002")

    def test_repository_search_can_find_a_person_by_code(self):
        person = Person.objects.create(
            nom="Bakayoko",
            prenom="Bakary",
            genre="M",
            famille=self.family,
        )
        repo = DjangoPersonRepository()

        persons, total = repo.get_all(q=person.code)
        autocomplete = repo.search_autocomplete(q=person.code)

        self.assertEqual(total, 1)
        self.assertEqual(persons[0].id, str(person.id))
        self.assertEqual(autocomplete[0].id, str(person.id))

    def test_update_use_case_rejects_conjoint_already_used_by_another_person(self):
        person = Person.objects.create(
            nom="Bakayoko",
            prenom="Abdoulaye",
            genre="M",
            famille=self.family,
        )
        conjoint_cible = Person.objects.create(
            nom="Traore",
            prenom="Aminata",
            genre="F",
            famille=self.family,
        )
        autre_personne = Person.objects.create(
            nom="Coulibaly",
            prenom="Moussa",
            genre="M",
            famille=self.family,
            conjoint=conjoint_cible,
        )

        use_case = UpdatePersonUseCase(
            DjangoPersonRepository(),
            DjangoFamilyRepository(),
        )

        with self.assertRaises(ConjointIndisponibleError):
            use_case.execute(
                UpdatePersonDTO(
                    id=str(person.id),
                    nom=person.nom,
                    prenom=person.prenom,
                    genre=person.genre,
                    famille_id=str(self.family.id),
                    conjoint_id=str(conjoint_cible.id),
                )
            )

    def test_create_use_case_accepts_free_text_parents_and_spouse_with_profession(self):
        use_case = CreatePersonUseCase(
            DjangoPersonRepository(),
            DjangoFamilyRepository(),
        )

        created = use_case.execute(
            CreatePersonDTO(
                nom="Bakayoko",
                prenom="Mariam",
                genre="F",
                famille_id=str(self.family.id),
                profession="Commercante",
                pere_nom_libre="Mamadou Traore",
                mere_nom_libre="Awa Traore",
                conjoint_nom_libre="Issa Coulibaly",
            )
        )

        self.assertIsNone(created.pere_id)
        self.assertEqual(created.pere_nom, "Mamadou Traore")
        self.assertEqual(created.pere_nom_libre, "Mamadou Traore")
        self.assertIsNone(created.mere_id)
        self.assertEqual(created.profession, "Commercante")
        self.assertEqual(created.mere_nom, "Awa Traore")
        self.assertEqual(created.mere_nom_libre, "Awa Traore")
        self.assertIsNone(created.conjoint_id)
        self.assertEqual(created.conjoint_nom, "Issa Coulibaly")
        self.assertEqual(created.conjoint_nom_libre, "Issa Coulibaly")

        person = Person.objects.get(id=created.id)
        self.assertFalse(person.est_chef_famille)

    def test_update_use_case_accepts_free_text_father_and_profession(self):
        person = Person.objects.create(
            nom="Bakayoko",
            prenom="Mariam",
            genre="F",
            famille=self.family,
        )
        father = Person.objects.create(
            nom="Traore",
            prenom="Mamadou",
            genre="M",
            famille=self.family,
        )

        use_case = UpdatePersonUseCase(
            DjangoPersonRepository(),
            DjangoFamilyRepository(),
        )

        updated = use_case.execute(
            UpdatePersonDTO(
                id=str(person.id),
                nom=person.nom,
                prenom=person.prenom,
                genre=person.genre,
                famille_id=str(self.family.id),
                profession="Infirmiere",
                pere_id=str(father.id),
                pere_nom_libre="Mamadou Konan",
            )
        )

        self.assertIsNone(updated.pere_id)
        self.assertEqual(updated.pere_nom, "Mamadou Konan")
        self.assertEqual(updated.pere_nom_libre, "Mamadou Konan")
        self.assertEqual(updated.profession, "Infirmiere")

    def test_create_use_case_rejects_a_second_family_head_in_same_family(self):
        Person.objects.create(
            nom="Bakayoko",
            prenom="Abdoulaye",
            genre="M",
            famille=self.family,
            est_chef_famille=True,
        )
        use_case = CreatePersonUseCase(
            DjangoPersonRepository(),
            DjangoFamilyRepository(),
        )

        with self.assertRaises(CreateChefFamilleDejaDefiniError):
            use_case.execute(
                CreatePersonDTO(
                    nom="Bakayoko",
                    prenom="Aminata",
                    genre="F",
                    famille_id=str(self.family.id),
                    est_chef_famille=True,
                )
            )

    def test_update_use_case_rejects_a_second_family_head_in_same_family(self):
        Person.objects.create(
            nom="Bakayoko",
            prenom="Abdoulaye",
            genre="M",
            famille=self.family,
            est_chef_famille=True,
        )
        person = Person.objects.create(
            nom="Bakayoko",
            prenom="Mariam",
            genre="F",
            famille=self.family,
        )
        use_case = UpdatePersonUseCase(
            DjangoPersonRepository(),
            DjangoFamilyRepository(),
        )

        with self.assertRaises(UpdateChefFamilleDejaDefiniError):
            use_case.execute(
                UpdatePersonDTO(
                    id=str(person.id),
                    nom=person.nom,
                    prenom=person.prenom,
                    genre=person.genre,
                    famille_id=str(self.family.id),
                    est_chef_famille=True,
                )
            )
