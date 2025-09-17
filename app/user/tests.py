"""Basic tests for user related views."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class UserViewsTests(TestCase):
    def test_login_page_renders(self) -> None:
        response = self.client.get(reverse("user:login"))
        self.assertEqual(response.status_code, 200)

    def test_profile_requires_authentication(self) -> None:
        response = self.client.get(reverse("user:profile"))
        self.assertEqual(response.status_code, 302)

    def test_authenticated_profile(self) -> None:
        user = User.objects.create_user(username="tester", password="secret")
        self.client.login(username="tester", password="secret")
        response = self.client.get(reverse("user:profile"))
        self.assertContains(response, "tester")

    def test_signup_flow(self) -> None:
        response = self.client.post(
            reverse("user:signup"),
            data={
                "username": "rider1",
                "nickname": "라이더",
                "email": "rider@example.com",
                "password1": "testpass123",
                "password2": "testpass123",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username="rider1").exists())
        self.assertTrue(response.context["user"].is_authenticated)
