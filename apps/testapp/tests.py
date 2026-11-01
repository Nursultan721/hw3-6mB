from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient


class SimpleJWTApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="jwt-client",
            email="client@example.com",
            password="Complex-test-password-483!",
        )
        self.client = APIClient()

    def get_tokens(self):
        response = self.client.post(
            reverse("token_obtain_pair"),
            {
                "email": "client@example.com",
                "password": "Complex-test-password-483!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_login_returns_tokens_and_user_details(self):
        data = self.get_tokens()

        self.assertIn("access", data)
        self.assertIn("refresh", data)
        self.assertEqual(
            {key: data[key] for key in ("id", "email", "username", "role")},
            {
                "id": self.user.pk,
                "email": "client@example.com",
                "username": "jwt-client",
                "role": "CLIENT",
            },
        )

    def test_profile_stats_requires_and_accepts_access_token(self):
        response = self.client.get(reverse("profile_stats"))
        self.assertEqual(response.status_code, 401)

        data = self.get_tokens()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {data['access']}")
        response = self.client.get(reverse("profile_stats"))

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["email"], self.user.email)
        self.assertEqual(response.data["role"], "CLIENT")
        self.assertFalse(response.data["is_staff"])
        self.assertIsNotNone(response.data["date_joined"])

    def test_logout_blacklists_refresh_token(self):
        data = self.get_tokens()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {data['access']}")
        response = self.client.post(
            reverse("logout"),
            {"refresh": data["refresh"]},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.post(
            reverse("token_refresh"),
            {"refresh": data["refresh"]},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_logout_rejects_another_users_refresh_token(self):
        other_user = get_user_model().objects.create_user(
            username="other",
            email="other@example.com",
            password="Complex-test-password-483!",
        )
        response = self.client.post(
            reverse("token_obtain_pair"),
            {
                "email": other_user.email,
                "password": "Complex-test-password-483!",
            },
            format="json",
        )
        other_refresh = response.data["refresh"]
        own_access = self.get_tokens()["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {own_access}")

        response = self.client.post(
            reverse("logout"),
            {"refresh": other_refresh},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_token_lifetimes_and_blacklist_app_are_configured(self):
        from django.conf import settings

        self.assertEqual(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"], timedelta(minutes=15))
        self.assertEqual(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"], timedelta(days=7))
        self.assertIn("rest_framework_simplejwt.token_blacklist", settings.INSTALLED_APPS)

# Create your tests here.
