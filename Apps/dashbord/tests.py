from datetime import timedelta

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from Apps.cotisations.models import ComptePaiement, Cotisation, Paiement
from Apps.events.models import Event
from Apps.families.models import Family
from Apps.histoire.models import ActionHistory
from Apps.person.models import Person
from Apps.villages.models import Infrastructure, Village
from Apps.website.models import PublicPersonSubmission


class PaginationTemplateTests(SimpleTestCase):
    def test_fixed_pagination_preserves_filters(self):
        html = render_to_string(
            "components/_pagination_fixed.html",
            {
                "page": 2,
                "nb_pages": 4,
                "total": 12,
                "par_page": 5,
                "display_start": 6,
                "display_end": 10,
                "q": "Nord",
                "infra": "ecole",
                "pop": "5000",
            },
        )

        self.assertIn("6-10", html)
        self.assertIn(
            "?page=1&q=Nord&infra=ecole&pop=5000&par_page=5",
            html,
        )
        self.assertIn(
            "?page=3&q=Nord&infra=ecole&pop=5000&par_page=5",
            html,
        )


class AdminDashboardViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="admin_dashboard",
            password="testpass123",
            role="admin",
        )

        cls.village_1 = Village.objects.create(
            nom="Olodio Centre",
            population_estimee=1200,
        )
        cls.village_2 = Village.objects.create(
            nom="Boka",
            population_estimee=750,
        )

        cls.family_1 = Family.objects.create(
            nom_famille="Kouassi",
            village=cls.village_1,
        )
        cls.family_2 = Family.objects.create(
            nom_famille="Diop",
            village=cls.village_2,
        )

        Person.objects.create(
            nom="Kouassi",
            prenom="Olivier",
            genre="M",
            famille=cls.family_1,
            est_chef_famille=True,
        )
        Person.objects.create(
            nom="Kouassi",
            prenom="Awa",
            genre="F",
            famille=cls.family_1,
        )
        Person.objects.create(
            nom="Diop",
            prenom="Sia",
            genre="F",
            famille=cls.family_2,
            type_residence="diaspora",
        )

        PublicPersonSubmission.objects.create(
            nom="Traore",
            prenom="Mariam",
            genre="F",
            famille=cls.family_1,
            est_vivant=True,
            type_residence="village",
            telephone="0701010101",
        )
        Event.objects.create(
            type="communaute",
            titre="Annonce en attente",
            resume="Annonce a valider.",
            description="Une nouvelle annonce publique doit etre relue.",
            date_evenement=timezone.localdate(),
            village=cls.village_1,
            est_public=True,
            statut_validation="pending",
        )

    def test_admin_dashboard_uses_live_database_metrics(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashbord:admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashbord/admin_dashboard.html")

        stats = response.context["dashboard_stats"]
        self.assertEqual(stats["total_personnes"], 3)
        self.assertEqual(stats["total_familles"], 2)
        self.assertEqual(stats["total_villages"], 2)
        self.assertEqual(stats["total_diaspora"], 1)
        self.assertEqual(stats["familles_verifiees"], 1)
        self.assertEqual(stats["villages_with_population"], 2)

        self.assertEqual(
            response.context["village_population_rows"][0]["nom"],
            "Olodio Centre",
        )
        self.assertEqual(response.context["gender_rows"][0]["count"], 2)
        self.assertEqual(response.context["gender_rows"][1]["count"], 1)

        self.assertContains(response, "Population recensee")
        self.assertContains(response, "Olodio Centre")
        self.assertContains(response, "Boka")
        self.assertContains(response, "Olivier Kouassi")
        self.assertContains(response, "Verifiee")
        self.assertContains(response, "A completer")

    def test_admin_layout_renders_search_and_logout_forms(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashbord:admin_dashboard"))

        self.assertContains(
            response,
            f'action="{reverse("dashbord:search")}"',
        )
        self.assertContains(response, 'name="q"')
        self.assertContains(
            response,
            f'action="{reverse("accounts:logout")}"',
            count=2,
        )

    def test_admin_layout_exposes_pending_submission_and_event_counts(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashbord:admin_dashboard"))

        self.assertEqual(response.context["pending_public_submissions_count"], 1)
        self.assertEqual(response.context["pending_events_count"], 1)
        self.assertEqual(response.context["notif_count"], 2)
        self.assertContains(response, "Dossiers publics en attente de verification")
        self.assertContains(
            response,
            "Annonces ou evenements en attente de validation",
        )

    def test_admin_search_view_groups_results_across_modules(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("dashbord:search"),
            {"q": "Olodio"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashbord/search_results.html")
        self.assertEqual(response.context["search_totals"]["villages"], 1)
        self.assertEqual(response.context["search_totals"]["families"], 1)
        self.assertEqual(response.context["search_totals"]["persons"], 2)
        self.assertContains(response, "Olodio Centre")
        self.assertContains(response, "Famille Kouassi")
        self.assertContains(response, "Olivier Kouassi")


class VillageListViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="admin_pagination",
            password="testpass123",
            role="admin",
        )

        for index in range(1, 13):
            Village.objects.create(
                nom=f"Village {index:02d}",
                population_estimee=index * 100,
            )

    def test_list_view_returns_only_requested_page(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("dashbord:village-list"),
            {"page": 2, "par_page": 5},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page"], 2)
        self.assertEqual(response.context["nb_pages"], 3)
        self.assertEqual(response.context["total"], 12)
        self.assertEqual(response.context["display_start"], 6)
        self.assertEqual(response.context["display_end"], 10)
        self.assertEqual(
            [village.nom for village in response.context["villages"]],
            [
                "Village 06",
                "Village 07",
                "Village 08",
                "Village 09",
                "Village 10",
            ],
        )
        self.assertContains(
            response,
            "?page=3&q=&infra=&pop=&par_page=5",
        )

    def test_list_view_falls_back_to_first_page_for_invalid_page(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("dashbord:village-list"),
            {"page": "abc", "par_page": 5},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page"], 1)
        self.assertEqual(response.context["display_start"], 1)
        self.assertEqual(response.context["display_end"], 5)

    def test_list_view_includes_delete_modal_script(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashbord:village-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "const villageDeleteUrlTemplate")
        self.assertContains(response, "function confirmerSuppression")


class UserListViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin = user_model.objects.create_user(
            username="admin_users",
            password="testpass123",
            role="admin",
        )
        cls.regular_user = user_model.objects.create_user(
            username="regular_users",
            password="testpass123",
            role="visiteur",
        )
        cls.village = Village.objects.create(
            nom="Olodio Admin",
            population_estimee=980,
        )
        cls.agent = user_model.objects.create_user(
            username="sarah",
            first_name="Sarah",
            last_name="Smith",
            email="sarah@example.com",
            password="testpass123",
            role="saisie",
            is_verified=True,
            village=cls.village,
            two_factor_method="email",
        )
        cls.agent.is_online = True
        cls.agent.last_login = timezone.now()
        cls.agent.save(update_fields=["is_online", "last_login"])

        cls.pending_user = user_model.objects.create_user(
            username="pending_user",
            first_name="Pending",
            last_name="Member",
            email="pending@example.com",
            password="testpass123",
            role="visiteur",
            is_verified=False,
        )
        cls.inactive_user = user_model.objects.create_user(
            username="inactive_user",
            first_name="Dormant",
            last_name="Diaspora",
            email="inactive@example.com",
            password="testpass123",
            role="diaspora",
            is_active=False,
        )

    def test_user_list_requires_admin_role(self):
        self.client.force_login(self.regular_user)

        response = self.client.get(reverse("dashbord:user-list"))

        self.assertEqual(response.status_code, 403)

    def test_user_list_renders_for_admin(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("dashbord:user-list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/liste_utilisateurs.html")
        self.assertContains(response, "Gestion des utilisateurs")
        self.assertContains(response, "Sarah Smith")
        self.assertContains(response, "Pending Member")
        self.assertGreaterEqual(response.context["stats"]["online_now"], 1)

    def test_user_list_filters_by_role_and_status(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("dashbord:user-list"),
            {"role": "saisie", "status": "verified"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total"], 1)
        self.assertContains(response, "Sarah Smith")
        self.assertNotContains(response, "Pending Member")


class UserCreateViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin = user_model.objects.create_user(
            username="admin_creator",
            password="testpass123",
            role="admin",
        )
        cls.regular_user = user_model.objects.create_user(
            username="simple_member",
            password="testpass123",
            role="visiteur",
        )
        cls.village = Village.objects.create(
            nom="Olodio Form",
            population_estimee=1500,
        )

    def test_user_create_requires_admin_role(self):
        self.client.force_login(self.regular_user)

        response = self.client.get(reverse("dashbord:user-create"))

        self.assertEqual(response.status_code, 403)

    def test_user_create_renders_form_for_admin(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("dashbord:user-create"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/formulaire_utilisateur.html")
        self.assertContains(response, "Creer un nouvel utilisateur")
        self.assertContains(response, 'name="temporary_password"')

    def test_user_create_persists_new_account(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("dashbord:user-create"),
            {
                "username": "nouveau.compte",
                "email": "nouveau.compte@example.com",
                "telephone": "0700000000",
                "temporary_password": "testpass12345",
                "role": "chef_village",
                "village": str(self.village.id),
                "is_verified": "on",
                "is_active": "on",
            },
        )

        self.assertRedirects(response, reverse("dashbord:user-list"))
        created_user = get_user_model().objects.get(username="nouveau.compte")
        self.assertEqual(created_user.email, "nouveau.compte@example.com")
        self.assertEqual(created_user.role, "chef_village")
        self.assertEqual(created_user.village, self.village)
        self.assertTrue(created_user.is_verified)
        self.assertTrue(created_user.is_active)
        self.assertFalse(created_user.is_staff)
        self.assertTrue(created_user.check_password("testpass12345"))


class EventDashboardViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin = user_model.objects.create_user(
            username="admin_events",
            password="testpass123",
            role="admin",
        )
        cls.regular_user = user_model.objects.create_user(
            username="visitor_events",
            password="testpass123",
            role="visiteur",
        )
        cls.agent = user_model.objects.create_user(
            username="agent_events",
            password="testpass123",
            role="saisie",
            first_name="Aminata",
            last_name="Events",
        )
        cls.village = Village.objects.create(
            nom="Olodio Event",
            population_estimee=2100,
        )
        cls.family = Family.objects.create(
            nom_famille="Konan",
            village=cls.village,
        )
        cls.person = Person.objects.create(
            nom="Konan",
            prenom="Awa",
            genre="F",
            famille=cls.family,
        )
        cls.event = Event.objects.create(
            type="mariage",
            titre="Mariage de Awa Konan",
            resume="Celebration familiale a Olodio Event.",
            description="Un grand mariage est annonce pour la communaute.",
            date_evenement=timezone.localdate(),
            village=cls.village,
            personne=cls.person,
            est_public=True,
            statut_validation="approved",
            valide_par=cls.admin,
            date_validation=timezone.now(),
        )
        cls.pending_public_event = Event.objects.create(
            type="communaute",
            titre="Demande web a verifier",
            resume="Annonce recue depuis l'accueil.",
            description="Une famille souhaite publier une annonce communautaire.",
            date_evenement=timezone.localdate() + timedelta(days=1),
            village=cls.village,
            est_public=True,
            statut_validation="pending",
            nom_contact="Awa Konan",
            telephone_contact="0701020304",
            email_contact="awa.konan@example.com",
        )

    def test_event_list_requires_registry_role(self):
        self.client.force_login(self.regular_user)

        response = self.client.get(reverse("dashbord:event-list"))

        self.assertEqual(response.status_code, 403)

    def test_event_list_renders_for_admin(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("dashbord:event-list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "events/liste_evenements.html")
        self.assertContains(response, "Actualites & annonces de la communaute")
        self.assertContains(response, "Mariage de Awa Konan")
        self.assertContains(response, "Demande web a verifier")

    def test_event_list_renders_for_agent_saisie(self):
        self.client.force_login(self.agent)

        response = self.client.get(reverse("dashbord:event-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Demande web a verifier")
        self.assertContains(response, "Demande depuis l'accueil")
        self.assertContains(
            response,
            reverse("dashbord:event-update", args=[self.pending_public_event.id]),
        )

    def test_event_list_uses_dashboard_review_links_instead_of_admin(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("dashbord:event-list"))

        self.assertContains(
            response,
            reverse("dashbord:event-update", args=[self.pending_public_event.id]),
        )
        self.assertNotContains(response, "/admin/events/event/")

    def test_event_create_publishes_event(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("dashbord:event-create"),
            {
                "titre": "Festival communautaire",
                "type": "communaute",
                "date_evenement": "2026-04-15",
                "resume": "Rencontre generale des villages.",
                "description": "Une grande rencontre est prevue avec les autorites.",
                "personne": "",
                "village": str(self.village.id),
                "lieu": "Place publique",
                "visibility_scope": "public",
                "submit_action": "publish",
            },
        )

        self.assertRedirects(response, reverse("dashbord:event-list"))
        created_event = Event.objects.get(titre="Festival communautaire")
        self.assertEqual(created_event.statut_validation, "approved")
        self.assertTrue(created_event.est_public)
        self.assertEqual(created_event.valide_par, self.admin)
        self.assertEqual(created_event.village, self.village)

    def test_event_create_is_available_to_agent_saisie(self):
        self.client.force_login(self.agent)

        response = self.client.get(reverse("dashbord:event-create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Creer une nouvelle annonce")

    def test_event_create_saves_draft(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("dashbord:event-create"),
            {
                "titre": "Brouillon actualite",
                "type": "autre",
                "date_evenement": "2026-04-18",
                "resume": "Actualite interne.",
                "description": "Cette annonce doit rester interne.",
                "personne": str(self.person.id),
                "village": "",
                "lieu": "",
                "visibility_scope": "private",
                "submit_action": "draft",
            },
        )

        self.assertRedirects(response, reverse("dashbord:event-list"))
        created_event = Event.objects.get(titre="Brouillon actualite")
        self.assertEqual(created_event.statut_validation, "pending")
        self.assertFalse(created_event.est_public)
        self.assertIsNone(created_event.valide_par)
        self.assertEqual(created_event.village, self.village)

    def test_agent_can_approve_public_event_from_dashboard(self):
        self.client.force_login(self.agent)

        response = self.client.post(
            reverse("dashbord:event-update", args=[self.pending_public_event.id]),
            {
                "titre": "Demande web a verifier",
                "type": "communaute",
                "date_evenement": (timezone.localdate() + timedelta(days=1)).isoformat(),
                "resume": "Annonce revue et validee.",
                "description": "Annonce revue puis validee depuis le dashboard agent.",
                "personne": "",
                "village": str(self.village.id),
                "lieu": "Place publique",
                "visibility_scope": "public",
                "submit_action": "publish",
            },
        )

        self.assertRedirects(response, reverse("dashbord:event-list"))

        self.pending_public_event.refresh_from_db()
        self.assertEqual(self.pending_public_event.statut_validation, "approved")
        self.assertEqual(self.pending_public_event.valide_par, self.agent)
        self.assertTrue(self.pending_public_event.est_public)

    def test_agent_can_reject_public_event_from_dashboard(self):
        self.client.force_login(self.agent)

        response = self.client.post(
            reverse("dashbord:event-update", args=[self.pending_public_event.id]),
            {
                "submit_action": "reject",
            },
        )

        self.assertRedirects(response, reverse("dashbord:event-list"))

        self.pending_public_event.refresh_from_db()
        self.assertEqual(self.pending_public_event.statut_validation, "rejected")
        self.assertEqual(self.pending_public_event.valide_par, self.agent)
        self.assertFalse(self.pending_public_event.est_public)


class CotisationDashboardViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin = user_model.objects.create_user(
            username="admin_cotisations",
            password="testpass123",
            role="admin",
        )
        cls.village = Village.objects.create(
            nom="Olodio Cotisation",
            population_estimee=1300,
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
        )
        cls.cotisation = Cotisation.objects.create(
            mois=4,
            annee=2026,
            famille=cls.family,
            statut="ouverte",
            description="Cotisation publique en attente de verification.",
        )
        cls.compte = ComptePaiement.objects.create(
            mode="wave",
            numero="0700112233",
            nom_titulaire="Association Olodio",
            est_actif=True,
        )
        cls.pending_payment = Paiement.objects.create(
            personne=cls.person,
            cotisation=cls.cotisation,
            compte_paiement=cls.compte,
            montant="5000",
            mode_paiement="wave",
            reference_transaction="WAVE-DETAIL-001",
            recu="cotisations/paiements/test-recu.jpg",
            est_soumission_publique=True,
            nom_soumetteur=cls.person.nom_complet,
            telephone_soumetteur="0712345678",
            email_soumetteur=cls.person.email,
            statut_validation="pending",
            notes="Paiement depose depuis le formulaire public.",
        )

    def test_detail_view_shows_pending_review_section_and_receipt_link(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("dashbord:cotisation-detail", args=[self.cotisation.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "cotisations/detail.html")
        self.assertContains(response, "Details de la cotisation")
        self.assertContains(response, "Demandes de paiement en attente")
        self.assertContains(response, "Voir le recu")
        self.assertContains(response, reverse("dashbord:paiement-update", args=[self.pending_payment.id]))

    def test_admin_can_approve_pending_payment_from_cotisation_detail(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("dashbord:cotisation-detail", args=[self.cotisation.id]),
            {
                "payment_id": str(self.pending_payment.id),
                "submit_action": "approve-payment",
            },
        )

        self.assertRedirects(
            response,
            reverse("dashbord:cotisation-detail", args=[self.cotisation.id]),
        )

        self.pending_payment.refresh_from_db()
        self.assertEqual(self.pending_payment.statut_validation, "approved")
        self.assertEqual(self.pending_payment.valide_par, self.admin)
        self.assertIsNotNone(self.pending_payment.date_validation)


class VillageDetailViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="admin_detail",
            password="testpass123",
            role="admin",
        )
        cls.village = Village.objects.create(
            nom="Gbeke-Ouattara",
            description="Village de demonstration pour le detail.",
            population_estimee=1240,
            chef_village="Kouadio N'Guessan",
            latitude=4.8521,
            longitude=-7.3842,
        )

    def test_detail_view_uses_detail_template(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("dashbord:village-detail", args=[self.village.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "village/detail.html")
        self.assertContains(response, "Gbeke-Ouattara")
        self.assertContains(response, 'id="village-map-detail"')
        self.assertContains(response, "mapbox-gl.css")


class VillageCreateViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="admin_create",
            password="testpass123",
            role="admin",
        )

    def test_create_view_uses_form_template(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashbord:village-create"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "village/formulaire.html")
        self.assertContains(response, 'id="village-map-preview"')
        self.assertContains(response, "MAPBOX_TOKEN")
        self.assertContains(response, "Créer le village")

    def test_create_view_lists_all_infrastructure_types(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashbord:village-create"))

        self.assertContains(response, "Type d'infrastructure")
        self.assertContains(response, "Nom de l'infrastructure")
        self.assertContains(response, "Capacité")
        self.assertContains(response, "Hôpital")
        self.assertContains(response, "Université")
        self.assertContains(response, "Autre")

    def test_create_view_persists_selected_infrastructures(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("dashbord:village-create"),
            {
                "nom": "Village Infra",
                "description": "Village avec infra detaillees",
                "population_estimee": 900,
                "chef_village": "Chef Infra",
                "latitude": "5.1234",
                "longitude": "-4.5678",
                "infra_id": ["", ""],
                "infra_type": ["ecole", "dispensaire"],
                "infra_name": [
                    "Ecole primaire de Blibouo",
                    "Dispensaire de Blibouo",
                ],
                "infra_state": ["moyen", "bon"],
                "infra_capacity": ["207", "45"],
                "infra_responsable": ["Bamba Aminata", "Coulibaly Marie"],
                "infra_contact": ["0702030405", "0703040506"],
            },
        )

        village = Village.objects.get(nom="Village Infra")

        self.assertRedirects(
            response,
            reverse("dashbord:village-detail", args=[village.id]),
        )
        infrastructures = list(
            village.infrastructures.filter(deleted__isnull=True).order_by("nom")
        )
        self.assertEqual(len(infrastructures), 2)
        self.assertEqual(infrastructures[0].type_infrastructure, "dispensaire")
        self.assertEqual(infrastructures[0].capacite, 45)
        self.assertEqual(infrastructures[0].responsable, "Coulibaly Marie")
        self.assertEqual(infrastructures[1].type_infrastructure, "ecole")
        self.assertEqual(infrastructures[1].capacite, 207)
        self.assertEqual(infrastructures[1].contact_responsable, "0702030405")


class VillageUpdateDeleteViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(
            username="admin_update_delete",
            password="testpass123",
            role="admin",
        )
        cls.village = Village.objects.create(
            nom="Village Editable",
            description="Version initiale",
            population_estimee=300,
            chef_village="Chef Initial",
        )

    def test_update_view_updates_village_and_quick_infrastructures(self):
        self.client.force_login(self.user)

        infrastructure = Infrastructure.objects.create(
            village=self.village,
            type_infrastructure="centre_sante",
            nom="Centre initial",
            etat="moyen",
            capacite=12,
            responsable="Chef initial",
            contact_responsable="0102030405",
        )

        response = self.client.post(
            reverse("dashbord:village-update", args=[self.village.id]),
            {
                "nom": "Village Editable",
                "description": "Version modifiee",
                "population_estimee": 450,
                "chef_village": "Chef Modifie",
                "latitude": "6.2000",
                "longitude": "-5.4000",
                "infra_id": [str(infrastructure.id), ""],
                "infra_type": ["centre_sante", "electricite"],
                "infra_name": ["Centre de sante central", "Raccordement principal"],
                "infra_state": ["bon", "en_construction"],
                "infra_capacity": ["35", ""],
                "infra_responsable": ["Chef Modifie", "Equipe technique"],
                "infra_contact": ["0700000001", "0700000002"],
            },
        )

        self.village.refresh_from_db()

        self.assertRedirects(
            response,
            reverse("dashbord:village-detail", args=[self.village.id]),
        )
        self.assertEqual(self.village.description, "Version modifiee")
        self.assertEqual(self.village.population_estimee, 450)
        self.assertEqual(self.village.chef_village, "Chef Modifie")
        infrastructures = {
            infra.type_infrastructure: infra
            for infra in self.village.infrastructures.filter(deleted__isnull=True)
        }
        self.assertEqual(set(infrastructures.keys()), {"centre_sante", "electricite"})
        self.assertEqual(infrastructures["centre_sante"].nom, "Centre de sante central")
        self.assertEqual(infrastructures["centre_sante"].capacite, 35)
        self.assertEqual(infrastructures["electricite"].etat, "en_construction")
        self.assertEqual(
            infrastructures["electricite"].responsable,
            "Equipe technique",
        )

    def test_update_view_does_not_render_extra_nested_delete_form(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("dashbord:village-update", args=[self.village.id])
        )

        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        form_start = html.index('<form id="formulaire-village"')
        infra_section = html.index('id="section-infrastructures"')
        form_segment = html[form_start:infra_section]
        self.assertEqual(form_segment.count("<form"), 1)
        self.assertContains(response, 'id="supprimer-village-form"')
        self.assertContains(response, 'form="supprimer-village-form"')

    def test_delete_view_soft_deletes_village(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("dashbord:village-delete", args=[self.village.id])
        )

        self.assertRedirects(response, reverse("dashbord:village-list"))
        self.assertFalse(Village.objects.filter(id=self.village.id).exists())


class AgentSaisiePermissionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin = user_model.objects.create_user(
            username="admin_registry",
            password="testpass123",
            role="admin",
        )
        cls.agent = user_model.objects.create_user(
            username="agent_registry",
            password="testpass123",
            role="saisie",
            first_name="Aminata",
            last_name="Saisie",
        )
        cls.village = Village.objects.create(
            nom="Village Agent",
            population_estimee=640,
            created_by=cls.admin,
        )
        cls.family = Family.objects.create(
            nom_famille="Kouadio",
            village=cls.village,
            created_by=cls.admin,
        )
        cls.agent_family = Family.objects.create(
            nom_famille="Soro",
            village=cls.village,
            created_by=cls.agent,
        )
        cls.person_owned = Person.objects.create(
            nom="Saisie",
            prenom="Awa",
            genre="F",
            famille=cls.family,
            created_by=cls.agent,
        )
        cls.person_other = Person.objects.create(
            nom="Konan",
            prenom="Jean",
            genre="M",
            famille=cls.family,
            created_by=cls.admin,
        )
        cls.public_submission = PublicPersonSubmission.objects.create(
            nom="Doe",
            prenom="Jane",
            genre="F",
            famille=cls.family,
            est_vivant=True,
            type_residence="village",
            telephone="0700001111",
            email="jane@example.com",
        )

    def test_agent_can_open_registry_create_forms(self):
        self.client.force_login(self.agent)

        person_response = self.client.get(reverse("dashbord:person-create"))
        family_response = self.client.get(reverse("dashbord:family-create"))
        village_response = self.client.get(reverse("dashbord:village-create"))

        self.assertEqual(person_response.status_code, 200)
        self.assertEqual(family_response.status_code, 200)
        self.assertEqual(village_response.status_code, 200)

    def test_agent_sees_only_owned_persons_in_list(self):
        self.client.force_login(self.agent)

        response = self.client.get(reverse("dashbord:person-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Awa")
        self.assertNotContains(response, "Jean")

    def test_agent_cannot_open_person_detail_for_other_author(self):
        self.client.force_login(self.agent)

        response = self.client.get(
            reverse("dashbord:person-detail", args=[self.person_other.id])
        )

        self.assertEqual(response.status_code, 403)

    def test_agent_cannot_delete_registry_entries(self):
        self.client.force_login(self.agent)

        person_response = self.client.post(
            reverse("dashbord:person-delete", args=[self.person_owned.id])
        )
        family_response = self.client.post(
            reverse("dashbord:family-delete", args=[self.agent_family.id])
        )
        village_response = self.client.post(
            reverse("dashbord:village-delete", args=[self.village.id])
        )

        self.assertEqual(person_response.status_code, 403)
        self.assertEqual(family_response.status_code, 403)
        self.assertEqual(village_response.status_code, 403)

    def test_agent_created_person_is_stamped_with_creator(self):
        self.client.force_login(self.agent)

        response = self.client.post(
            reverse("dashbord:person-create"),
            {
                "nom": "Doe",
                "prenom": "Jane",
                "genre": "F",
                "famille_id": str(self.family.id),
                "nationalite": "Ivoirienne",
                "situation_matrimoniale": "celibataire",
                "type_residence": "village",
            },
        )

        created_person = Person.objects.get(nom="Doe", prenom="Jane")
        self.assertRedirects(
            response,
            reverse("dashbord:person-detail", args=[created_person.id]),
        )
        self.assertEqual(created_person.created_by, self.agent)

    def test_agent_can_review_public_submissions(self):
        self.client.force_login(self.agent)

        response = self.client.get(
            reverse("dashbord:public-person-submission-list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pre-inscriptions publiques")
        self.assertContains(response, "Jane Doe")

    def test_agent_can_approve_public_submission_into_person_record(self):
        self.client.force_login(self.agent)

        response = self.client.post(
            reverse(
                "dashbord:public-person-submission-review",
                args=[self.public_submission.id],
            ),
            {
                "nom": "Doe",
                "prenom": "Jane",
                "genre": "F",
                "famille_id": str(self.family.id),
                "nationalite": "Ivoirienne",
                "situation_matrimoniale": "celibataire",
                "type_residence": "village",
                "est_vivant": "on",
                "telephone": "0700001111",
                "email": "jane@example.com",
            },
        )

        created_person = Person.objects.get(nom="Doe", prenom="Jane")
        self.assertRedirects(
            response,
            reverse("dashbord:person-detail", args=[created_person.id]),
        )

        self.public_submission.refresh_from_db()
        self.assertEqual(self.public_submission.statut_validation, "approved")
        self.assertEqual(self.public_submission.personne_creee, created_person)
        self.assertEqual(self.public_submission.valide_par, self.agent)
        self.assertEqual(created_person.created_by, self.agent)


class ActionHistoryAuditTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin = user_model.objects.create_user(
            username="admin_history",
            password="testpass123",
            role="admin",
            first_name="Moussa",
            last_name="Historique",
        )
        cls.village = Village.objects.create(
            nom="Village Historique",
            population_estimee=500,
            created_by=cls.admin,
        )

    def test_authenticated_dashboard_request_creates_action_history(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("dashbord:village-list"))

        self.assertEqual(response.status_code, 200)
        history_entry = ActionHistory.objects.filter(
            user=self.admin,
            fonction="dashbord:village-list",
        ).first()
        self.assertIsNotNone(history_entry)
        self.assertEqual(history_entry.action, "Consultation")
        self.assertEqual(history_entry.user_name, "Moussa Historique")
        self.assertEqual(history_entry.pays, "Réseau local")
        self.assertEqual(history_entry.ville, "Local")

    def test_action_history_page_requires_admin(self):
        user_model = get_user_model()
        regular_user = user_model.objects.create_user(
            username="simple_history",
            password="testpass123",
            role="visiteur",
        )
        self.client.force_login(regular_user)

        response = self.client.get(reverse("dashbord:action-history"))

        self.assertEqual(response.status_code, 403)
