from django.test import TestCase
from django.urls import reverse

from Apps.cotisations.models import ComptePaiement, Cotisation, Paiement
from Apps.events.models import Event
from Apps.families.models import Family
from Apps.person.models import Person
from Apps.villages.models import Village
from Apps.website.models import PublicPersonSubmission


class PublicPersonRegistrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.village = Village.objects.create(
            nom="Olodio Centre",
            population_estimee=1200,
        )
        cls.family = Family.objects.create(
            nom_famille="Kouassi",
            village=cls.village,
        )

    def test_registration_page_renders(self):
        response = self.client.get(reverse("website:person-register"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "person_register.html")
        self.assertContains(response, "Famille d'appartenance")
        self.assertContains(response, self.family.nom_famille)

    def test_registration_post_creates_pending_submission(self):
        response = self.client.post(
            reverse("website:person-register"),
            data={
                "nom": "Doe",
                "prenom": "Jane",
                "genre": "F",
                "famille_id": str(self.family.id),
                "est_vivant": "on",
                "type_residence": "village",
            },
        )

        self.assertRedirects(response, reverse("website:person-register"))
        self.assertFalse(Person.objects.filter(nom="Doe", prenom="Jane").exists())
        self.assertTrue(
            PublicPersonSubmission.objects.filter(nom="Doe", prenom="Jane").exists()
        )

        submission = PublicPersonSubmission.objects.get(nom="Doe", prenom="Jane")
        self.assertEqual(submission.famille, self.family)
        self.assertEqual(submission.genre, "F")
        self.assertTrue(submission.est_vivant)
        self.assertEqual(submission.statut_validation, "pending")

    def test_homepage_exposes_registration_links(self):
        response = self.client.get(reverse("website:accueil"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("website:person-register"), count=3)
        self.assertContains(response, reverse("website:cotisation-payment-submit"))


class PublicEventSubmissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.village = Village.objects.create(
            nom="Dabolodio",
            population_estimee=900,
        )

    def test_submission_page_renders(self):
        response = self.client.get(reverse("website:event-submit"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "public_event_submit.html")
        self.assertContains(response, "Soumettre une annonce")
        self.assertContains(response, self.village.nom)

    def test_submission_post_creates_pending_public_event(self):
        response = self.client.post(
            reverse("website:event-submit"),
            data={
                "nom_contact": "Kouadio Amani",
                "telephone_contact": "0701020304",
                "email_contact": "amani@example.com",
                "village": str(self.village.id),
                "type": "communaute",
                "titre": "Reunion des jeunes du village",
                "date_evenement": "2026-04-12",
                "lieu": "Foyer des jeunes",
                "resume": "Preparation de la fete du village.",
                "description": "Tous les jeunes du village sont invites a une reunion preparatoire.",
            },
        )

        self.assertRedirects(response, reverse("website:event-submit"))
        event = Event.objects.get(titre="Reunion des jeunes du village")
        self.assertEqual(event.statut_validation, "pending")
        self.assertTrue(event.est_public)
        self.assertEqual(event.village, self.village)
        self.assertEqual(event.nom_contact, "Kouadio Amani")
        self.assertEqual(event.telephone_contact, "0701020304")

    def test_homepage_exposes_public_submission_links(self):
        response = self.client.get(reverse("website:accueil"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("website:event-submit"), count=4)
        self.assertContains(response, reverse("website:cotisation-payment-submit"))


class PublicCotisationPaymentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.village = Village.objects.create(
            nom="Olodio Mission",
            population_estimee=750,
        )
        cls.family = Family.objects.create(
            nom_famille="Yao",
            village=cls.village,
        )
        cls.person = Person.objects.create(
            nom="Yao",
            prenom="Aminata",
            genre="F",
            famille=cls.family,
            telephone="0700000000",
            email="aminata@example.com",
            type_residence="village",
        )
        cls.cotisation = Cotisation.objects.create(
            mois=4,
            annee=2026,
            famille=cls.family,
            statut="ouverte",
            description="Cotisation LBS avril",
        )
        cls.compte = ComptePaiement.objects.create(
            mode="wave",
            numero="0700112233",
            nom_titulaire="Association LBS",
            est_actif=True,
            ordre_affichage=1,
        )

    def test_payment_page_renders(self):
        response = self.client.get(reverse("website:cotisation-payment-submit"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "public_cotisation_payment.html")
        self.assertContains(response, "Envoyer une demande de validation de paiement")
        self.assertContains(response, self.compte.numero)
        self.assertNotContains(response, 'name="nom_soumetteur"', html=False)
        self.assertNotContains(response, 'name="email_soumetteur"', html=False)
        self.assertContains(response, "Numero utilise pour la transaction")

    def test_payment_post_creates_pending_public_payment(self):
        response = self.client.post(
            reverse("website:cotisation-payment-submit"),
            data={
                "telephone_soumetteur": "0712345678",
                "personne": str(self.person.id),
                "cotisation": str(self.cotisation.id),
                "montant": "5000",
                "date_paiement": "2026-04-20",
                "mode_paiement": "wave",
                "compte_paiement": str(self.compte.id),
                "reference_transaction": "WAVE-123456",
                "notes": "Depot envoye depuis le site public.",
            },
        )

        self.assertRedirects(response, reverse("website:cotisation-payment-submit"))
        paiement = Paiement.objects.get(reference_transaction="WAVE-123456")
        self.assertEqual(paiement.personne, self.person)
        self.assertEqual(paiement.cotisation, self.cotisation)
        self.assertEqual(paiement.statut_validation, "pending")
        self.assertTrue(paiement.est_soumission_publique)
        self.assertEqual(paiement.nom_soumetteur, self.person.nom_complet)
        self.assertEqual(paiement.telephone_soumetteur, "0712345678")
        self.assertEqual(paiement.email_soumetteur, self.person.email)
        self.assertIsNone(paiement.enregistre_par)
        self.assertIsNone(paiement.valide_par)
