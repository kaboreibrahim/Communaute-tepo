from django.core.exceptions import ValidationError
from django.test import TestCase

from Apps.cotisations.models import (
    ComptePaiement,
    Cotisation,
    CotisationPersonne,
    Paiement,
)
from Apps.families.models import Family
from Apps.person.models import Person
from Apps.villages.models import Village


class CotisationModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.village = Village.objects.create(nom="Olodio")
        cls.other_village = Village.objects.create(nom="Boubou")
        cls.family = Family.objects.create(
            nom_famille="Kone",
            village=cls.village,
        )
        cls.other_family = Family.objects.create(
            nom_famille="Traore",
            village=cls.other_village,
        )
        cls.person = Person.objects.create(
            nom="Kone",
            prenom="Aminata",
            genre="F",
            famille=cls.family,
        )
        cls.other_person = Person.objects.create(
            nom="Traore",
            prenom="Moussa",
            genre="M",
            famille=cls.other_family,
        )
        cls.compte = ComptePaiement.objects.create(
            mode="wave",
            numero="0707070707",
            nom_titulaire="Association Olodio",
        )

    def test_family_cotisation_infers_village(self):
        cotisation = Cotisation.objects.create(
            mois=1,
            annee=2026,
            famille=self.family,
        )
        self.assertEqual(cotisation.village, self.village)

    def test_general_cotisation_can_be_created_without_scope(self):
        cotisation = Cotisation.objects.create(
            mois=1,
            annee=2027,
            est_generale=True,
        )
        self.assertIsNone(cotisation.village)
        self.assertIsNone(cotisation.famille)
        self.assertCountEqual(
            list(cotisation.personnes_cibles.values_list("id", flat=True)),
            [self.person.id, self.other_person.id],
        )

    def test_general_cotisation_has_specific_label(self):
        cotisation = Cotisation.objects.create(
            mois=2,
            annee=2027,
            est_generale=True,
        )
        self.assertIn("toutes les personnes", cotisation.cible_label.lower())

    def test_payment_rejects_person_outside_scope(self):
        cotisation = Cotisation.objects.create(
            mois=2,
            annee=2026,
            village=self.village,
        )
        paiement = Paiement(
            personne=self.other_person,
            cotisation=cotisation,
            montant="5000.00",
            mode_paiement="wave",
            compte_paiement=self.compte,
        )
        with self.assertRaises(ValidationError):
            paiement.full_clean()

    def test_payment_requires_matching_account_mode(self):
        cotisation = Cotisation.objects.create(
            mois=3,
            annee=2026,
            famille=self.family,
        )
        paiement = Paiement(
            personne=self.person,
            cotisation=cotisation,
            montant="5000.00",
            mode_paiement="mtn",
            compte_paiement=self.compte,
        )
        with self.assertRaises(ValidationError):
            paiement.full_clean()

    def test_cotisation_tracks_total_collected(self):
        cotisation = Cotisation.objects.create(
            mois=4,
            annee=2026,
            famille=self.family,
        )
        Paiement.objects.create(
            personne=self.person,
            cotisation=cotisation,
            montant="5000.00",
            mode_paiement="wave",
            compte_paiement=self.compte,
            statut_validation="approved",
        )
        self.assertEqual(cotisation.total_collecte, 5000)
        self.assertEqual(cotisation.nombre_payeurs, 1)

    def test_tracking_rejects_person_outside_scope(self):
        cotisation = Cotisation.objects.create(
            mois=5,
            annee=2026,
            famille=self.family,
        )
        suivi = CotisationPersonne(
            cotisation=cotisation,
            personne=self.other_person,
            montant_attendu="3000.00",
        )
        with self.assertRaises(ValidationError):
            suivi.full_clean()

    def test_tracking_calculates_remaining_amount(self):
        cotisation = Cotisation.objects.create(
            mois=6,
            annee=2026,
            famille=self.family,
        )
        suivi = CotisationPersonne.objects.create(
            cotisation=cotisation,
            personne=self.person,
            montant_attendu="8000.00",
        )
        Paiement.objects.create(
            personne=self.person,
            cotisation=cotisation,
            montant="5000.00",
            mode_paiement="wave",
            compte_paiement=self.compte,
            statut_validation="approved",
        )

        self.assertEqual(suivi.total_paye, 5000)
        self.assertEqual(suivi.reste_a_payer, 3000)
        self.assertEqual(suivi.statut_suivi, "partiel")

    def test_payment_save_creates_person_tracking(self):
        cotisation = Cotisation.objects.create(
            mois=7,
            annee=2026,
            famille=self.family,
        )
        Paiement.objects.create(
            personne=self.person,
            cotisation=cotisation,
            montant="2500.00",
            mode_paiement="wave",
            compte_paiement=self.compte,
            statut_validation="approved",
        )

        self.assertTrue(
            CotisationPersonne.objects.filter(
                cotisation=cotisation,
                personne=self.person,
            ).exists()
        )
