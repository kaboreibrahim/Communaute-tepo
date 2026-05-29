from datetime import timedelta

import pyotp
from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY, get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from Apps.accounts.models.code import CodeVerification
from Apps.accounts.services.auth_service import AuthService


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class LoginFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = "secret123"
        cls.user = get_user_model().objects.create_user(
            username="admin",
            email="admin@example.com",
            password=cls.password,
            role="admin",
        )

    def _mark_as_returning_user(self, user):
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

    def _start_login(self, user, identifier=None):
        return self.client.post(
            reverse("accounts:login"),
            {
                "username": identifier or user.username,
                "password": self.password,
            },
        )

    def test_first_login_redirects_to_two_factor_method_when_no_method_is_configured(self):
        response = self._start_login(self.user)

        self.assertRedirects(response, reverse("accounts:two_factor_method"))
        self.assertEqual(
            self.client.session[AuthService.PRE_2FA_USER_ID_KEY],
            str(self.user.id),
        )
        self.assertNotIn(BACKEND_SESSION_KEY, self.client.session)

    def test_email_login_identifier_also_redirects_to_method_setup_when_unconfigured(self):
        response = self._start_login(self.user, self.user.email)

        self.assertRedirects(response, reverse("accounts:two_factor_method"))
        self.assertEqual(
            self.client.session[AuthService.PRE_2FA_USER_ID_KEY],
            str(self.user.id),
        )
        self.assertNotIn(BACKEND_SESSION_KEY, self.client.session)

    def test_first_login_redirects_to_two_factor_method_even_when_method_is_preconfigured(self):
        user = get_user_model().objects.create_user(
            username="email_first_login",
            email="email_first_login@example.com",
            password=self.password,
            role="admin",
            two_factor_method="email",
        )

        response = self._start_login(user)

        self.assertRedirects(response, reverse("accounts:two_factor_method"))
        self.assertEqual(len(mail.outbox), 0)
        self.assertNotIn(AuthService.EMAIL_2FA_CODE_KEY, self.client.session)
        self.assertNotIn(BACKEND_SESSION_KEY, self.client.session)

    def test_two_factor_method_email_selection_starts_email_verification(self):
        self._start_login(self.user)

        response = self.client.post(
            reverse("accounts:two_factor_method"),
            {"two_factor_method": "email"},
        )

        self.assertRedirects(response, reverse("accounts:email_verification"))
        self.assertIn(AuthService.EMAIL_2FA_CODE_KEY, self.client.session)
        self.assertEqual(len(mail.outbox), 1)
        self.user.refresh_from_db()
        self.assertEqual(self.user.two_factor_method, "email")

    def test_two_factor_method_google_selection_redirects_to_setup(self):
        self._start_login(self.user)

        response = self.client.post(
            reverse("accounts:two_factor_method"),
            {"two_factor_method": "google_auth"},
        )

        self.assertRedirects(response, reverse("accounts:google_auth_setup"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.two_factor_method, "google_auth")

    def test_google_auth_login_redirects_to_two_factor_method_when_not_confirmed(self):
        user = get_user_model().objects.create_user(
            username="google_setup",
            email="google_setup@example.com",
            password=self.password,
            role="admin",
            two_factor_method="google_auth",
            google_auth_confirmed=False,
        )
        self._mark_as_returning_user(user)

        response = self._start_login(user)

        self.assertRedirects(response, reverse("accounts:two_factor_method"))
        self.assertEqual(
            self.client.session[AuthService.PRE_2FA_USER_ID_KEY],
            str(user.id),
        )
        self.assertNotIn(BACKEND_SESSION_KEY, self.client.session)

    def test_google_auth_setup_with_valid_code_completes_login(self):
        user = get_user_model().objects.create_user(
            username="google_first_login",
            email="google_first_login@example.com",
            password=self.password,
            role="admin",
            two_factor_method="google_auth",
            google_auth_confirmed=False,
        )
        self._mark_as_returning_user(user)

        login_response = self._start_login(user)
        self.assertRedirects(login_response, reverse("accounts:two_factor_method"))

        selection_response = self.client.post(
            reverse("accounts:two_factor_method"),
            {"two_factor_method": "google_auth"},
        )
        self.assertRedirects(selection_response, reverse("accounts:google_auth_setup"))
        setup_response = self.client.get(reverse("accounts:google_auth_setup"))

        self.assertEqual(setup_response.status_code, 200)

        user.refresh_from_db()
        code = pyotp.TOTP(user.google_auth_secret).now()

        response = self.client.post(
            reverse("accounts:google_auth_setup"),
            {"code": code},
        )

        self.assertRedirects(response, reverse("dashbord:admin_dashboard"))
        user.refresh_from_db()
        self.assertTrue(user.google_auth_confirmed)
        self.assertEqual(
            self.client.session[BACKEND_SESSION_KEY],
            settings.AUTHENTICATION_BACKENDS[0],
        )

    def test_google_auth_login_redirects_to_two_factor_method_when_confirmed(self):
        user = get_user_model().objects.create_user(
            username="google_verify",
            email="google_verify@example.com",
            password=self.password,
            role="admin",
            two_factor_method="google_auth",
            google_auth_secret=pyotp.random_base32(),
            google_auth_confirmed=True,
        )
        self._mark_as_returning_user(user)

        response = self._start_login(user)

        self.assertRedirects(response, reverse("accounts:two_factor_method"))
        self.assertEqual(
            self.client.session[AuthService.PRE_2FA_USER_ID_KEY],
            str(user.id),
        )
        self.assertNotIn(BACKEND_SESSION_KEY, self.client.session)

    def test_two_factor_method_google_selection_redirects_to_verification_when_confirmed(self):
        user = get_user_model().objects.create_user(
            username="google_verify_choice",
            email="google_verify_choice@example.com",
            password=self.password,
            role="admin",
            two_factor_method="google_auth",
            google_auth_secret=pyotp.random_base32(),
            google_auth_confirmed=True,
        )
        self._mark_as_returning_user(user)
        self._start_login(user)

        response = self.client.post(
            reverse("accounts:two_factor_method"),
            {"two_factor_method": "google_auth"},
        )

        self.assertRedirects(response, reverse("accounts:google_auth_verification"))

    def test_google_auth_verification_accepts_valid_code(self):
        secret = pyotp.random_base32()
        user = get_user_model().objects.create_user(
            username="google_valid_code",
            email="google_valid_code@example.com",
            password=self.password,
            role="admin",
            two_factor_method="google_auth",
            google_auth_secret=secret,
            google_auth_confirmed=True,
        )
        self._mark_as_returning_user(user)

        self._start_login(user)
        selection_response = self.client.post(
            reverse("accounts:two_factor_method"),
            {"two_factor_method": "google_auth"},
        )
        self.assertRedirects(selection_response, reverse("accounts:google_auth_verification"))

        response = self.client.post(
            reverse("accounts:google_auth_verification"),
            {"code": pyotp.TOTP(secret).now()},
        )

        self.assertRedirects(response, reverse("dashbord:admin_dashboard"))
        self.assertEqual(
            self.client.session[BACKEND_SESSION_KEY],
            settings.AUTHENTICATION_BACKENDS[0],
        )

    def test_email_2fa_message_uses_olodio_context(self):
        user = get_user_model().objects.create_user(
            username="email_2fa",
            email="email_2fa@example.com",
            password=self.password,
            role="admin",
            two_factor_method="email",
        )
        self._mark_as_returning_user(user)

        login_response = self._start_login(user)
        self.assertRedirects(login_response, reverse("accounts:two_factor_method"))

        response = self.client.post(
            reverse("accounts:two_factor_method"),
            {"two_factor_method": "email"},
        )

        self.assertRedirects(response, reverse("accounts:email_verification"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Olodio Platform", mail.outbox[0].subject)
        self.assertIn("Sous-prefecture d'Olodio", mail.outbox[0].alternatives[0][0])
        self.assertNotIn("Sourcing", mail.outbox[0].alternatives[0][0])

    def test_email_2fa_requires_configured_email(self):
        user = get_user_model().objects.create_user(
            username="email_missing",
            email="",
            password=self.password,
            role="admin",
            two_factor_method="email",
        )
        self._mark_as_returning_user(user)

        login_response = self._start_login(user)
        self.assertRedirects(login_response, reverse("accounts:two_factor_method"))

        response = self.client.post(
            reverse("accounts:two_factor_method"),
            {"two_factor_method": "email"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aucune adresse email")
        self.assertNotIn(AuthService.EMAIL_2FA_CODE_KEY, self.client.session)
        self.assertNotIn(BACKEND_SESSION_KEY, self.client.session)

    @patch("Apps.accounts.views.auth_views.AuthService.send_2fa_email")
    def test_email_2fa_send_failure_redirects_to_method_selection(self, mock_send_2fa_email):
        mock_send_2fa_email.side_effect = RuntimeError("SMTP error")
        user = get_user_model().objects.create_user(
            username="email_failure",
            email="email_failure@example.com",
            password=self.password,
            role="admin",
            two_factor_method="email",
        )
        self._mark_as_returning_user(user)

        login_response = self._start_login(user)
        self.assertRedirects(login_response, reverse("accounts:two_factor_method"))

        response = self.client.post(
            reverse("accounts:two_factor_method"),
            {"two_factor_method": "email"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SMTP error")
        self.assertNotIn(AuthService.EMAIL_2FA_CODE_KEY, self.client.session)
        self.assertNotIn(BACKEND_SESSION_KEY, self.client.session)

    def test_logout_message_is_displayed_on_public_home_and_not_leaked(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("accounts:logout"), follow=True)

        self.assertContains(response, "Vous etes deconnecte.")
        follow_up = self.client.get(reverse("accounts:login"))
        self.assertNotContains(follow_up, "Vous etes deconnecte.")


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AccountsAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = get_user_model().objects.create_superuser(
            username="admin_root",
            email="admin_root@example.com",
            password="secret123",
        )
        cls.user = get_user_model().objects.create_user(
            username="member",
            email="member@example.com",
            password="secret123",
            role="visiteur",
            is_verified=True,
        )
        CodeVerification.objects.create(
            user=cls.user,
            code="ABC123",
            type_code="activation",
            email=cls.user.email,
            expires_at=timezone.now() + timedelta(minutes=5),
            is_used=False,
            attempts=0,
            max_attempts=3,
        )

    def test_utilisateur_changelist_renders(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin:accounts_utilisateur_changelist"))

        self.assertEqual(response.status_code, 200)

    def test_codeverification_changelist_renders(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin:accounts_codeverification_changelist"))

        self.assertEqual(response.status_code, 200)

    def test_utilisateur_change_view_renders(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse("admin:accounts_utilisateur_change", args=[self.user.pk])
        )

        self.assertEqual(response.status_code, 200)
