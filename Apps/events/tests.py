from datetime import timedelta

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from Apps.events.models import Event
from Apps.families.models import Family
from Apps.person.models import Person
from Apps.villages.models import Village


class EventModerationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.village = Village.objects.create(
            nom="Olodio Centre",
        )
        cls.family = Family.objects.create(
            nom_famille="Kouassi",
            village=cls.village,
        )
        cls.person = Person.objects.create(
            nom="Kouassi",
            prenom="Awa",
            genre="F",
            famille=cls.family,
        )

        today = timezone.localdate()

        cls.approved_public_event = Event.objects.create(
            type="mariage",
            titre="Mariage de Awa et Koffi",
            resume="Union celebree avec la benediction de la famille.",
            description="Description detaillee du mariage de Awa et Koffi avec toutes les informations utiles pour la famille et les invites.",
            date_evenement=today - timedelta(days=1),
            lieu="Olodio Centre",
            personne=cls.person,
            est_public=True,
            statut_validation="approved",
        )
        cls.pending_event = Event.objects.create(
            type="deces",
            titre="Annonce en attente",
            description="Cet evenement ne doit pas encore etre visible.",
            date_evenement=today,
            personne=cls.person,
            est_public=True,
            statut_validation="pending",
        )
        cls.private_event = Event.objects.create(
            type="naissance",
            titre="Annonce privee",
            date_evenement=today,
            personne=cls.person,
            est_public=False,
            statut_validation="approved",
        )
        cls.community_event = Event.objects.create(
            type="communaute",
            titre="Festival des Arts Kroumen",
            description="Rencontre culturelle sur la place publique.",
            date_evenement=today + timedelta(days=4),
            lieu="Place publique d'Olodio",
            est_public=True,
            statut_validation="approved",
        )

    def test_event_admin_is_registered(self):
        self.assertIn(Event, admin.site._registry)

    def test_admin_add_view_renders_without_crashing(self):
        admin_user = get_user_model().objects.create_user(
            username="event_admin",
            email="event_admin@example.com",
            password="testpass123",
            role="admin",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse("admin:events_event_add"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "En attente de moderation")

    def test_event_is_pending_by_default(self):
        event = Event.objects.create(
            type="autre",
            titre="Annonce test",
            date_evenement=timezone.localdate(),
        )

        self.assertEqual(event.statut_validation, "pending")
        self.assertFalse(event.est_valide)
        self.assertFalse(event.publie_sur_accueil)

    def test_homepage_only_shows_approved_public_events(self):
        response = self.client.get(reverse("website:accueil"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mariage de Awa et Koffi")
        self.assertContains(response, "Festival des Arts Kroumen")
        self.assertNotContains(response, "Annonce en attente")
        self.assertNotContains(response, "Annonce privee")

    def test_homepage_exposes_community_events_in_agenda(self):
        response = self.client.get(reverse("website:accueil"))

        self.assertEqual(response.status_code, 200)
        agenda_titles = [item["title"] for item in response.context["agenda_events"]]
        self.assertIn("Festival des Arts Kroumen", agenda_titles)

    def test_homepage_news_cards_include_modal_payload(self):
        response = self.client.get(reverse("website:accueil"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-news-modal')
        self.assertContains(response, 'community-news-modal-title')
        self.assertContains(
            response,
            'aria-label="Afficher les details de Festival des Arts Kroumen"',
        )
        self.assertContains(
            response,
            'aria-label="Afficher les details de Mariage de Awa et Koffi"',
        )
        self.assertContains(response, "Rencontre culturelle sur la place publique.")
        self.assertContains(
            response,
            "Description detaillee du mariage de Awa et Koffi avec toutes les informations utiles pour la famille et les invites.",
        )
