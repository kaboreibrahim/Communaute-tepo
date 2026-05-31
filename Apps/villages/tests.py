from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from Apps.villages.models import Village


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class VillageAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="secret123",
        )
        cls.village = Village.objects.create(
            nom="Olodio",
            chef_village="Chef Test",
        )

    def test_admin_add_view_renders_without_format_html_error(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin:villages_village_add"))

        self.assertEqual(response.status_code, 200)

    def test_admin_changelist_renders_without_familles_relation(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin:villages_village_changelist"))

        self.assertEqual(response.status_code, 200)
