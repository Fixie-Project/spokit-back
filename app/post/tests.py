"""Basic smoke tests for the post app."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Comment, Post, PostStatus


class PostViewsTests(TestCase):
    def setUp(self) -> None:
        self.post = Post.objects.create(
            title="첫 글",
            slug="first-post",
            summary="요약",
            body="내용",
            status=PostStatus.PUBLISHED,
            published_at=timezone.now(),
        )

    def test_list_view(self) -> None:
        response = self.client.get(reverse("post:list"))
        self.assertContains(response, "첫 글")

    def test_detail_view(self) -> None:
        response = self.client.get(self.post.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "내용")

    def test_comment_requires_login(self) -> None:
        response = self.client.post(
            self.post.get_absolute_url(),
            data={"content": "안녕하세요"},
        )
        self.assertEqual(response.status_code, 302)

    def test_authenticated_comment(self) -> None:
        user = get_user_model().objects.create_user(
            username="tester", email="tester@example.com", password="secret123"
        )
        self.client.login(username="tester", password="secret123")
        response = self.client.post(
            self.post.get_absolute_url(),
            data={"content": "좋은 빌드네요"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Comment.objects.filter(post=self.post, user=user, content__contains="좋은").exists()
        )
