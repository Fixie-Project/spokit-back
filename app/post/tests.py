"""Basic smoke tests for post interactions."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from app.bike.models import Bike, BikeBuild, FrameType

from .models import Comment, Post, PostStatus


class PostInteractionTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            email="tester@example.com",
            username="tester",
            nickname="tester",
            password="secret123",
        )
        self.bike = Bike.objects.create(
            owner=self.user,
            frame_name="Affinity LoPro",
            is_public=True,
            is_posted=True,
        )
        self.build = BikeBuild.objects.create(base_bike=self.bike, components={}, note="")
        self.post = Post.objects.create(
            bike=self.bike,
            build=self.build,
            build_snapshot={"frame": "Affinity"},
            main_title="첫 글",
            sub_title="테스트",
            content_md="",
            content_html="<p>내용</p>",
            content_json={"type": "doc", "content": []},
            frame_brand="Affinity",
            frame_type=FrameType.ALLOY,
            slug="first-post",
            status=PostStatus.PUBLISHED,
        )

    def test_comment_requires_login(self) -> None:
        url = reverse("post:comment", kwargs={"slug": self.post.slug})
        response = self.client.post(url, data={"content": "안녕하세요"})
        self.assertIn(response.status_code, {401, 403})

    def test_authenticated_comment(self) -> None:
        self.client.login(username="tester@example.com", password="secret123")
        url = reverse("post:comment", kwargs={"slug": self.post.slug})
        response = self.client.post(url, data={"content": "좋은 빌드네요"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Comment.objects.filter(post=self.post, user=self.user, content__contains="좋은").exists()
        )

    def test_like_toggle(self) -> None:
        self.client.login(username="tester@example.com", password="secret123")
        url = reverse("post:like", kwargs={"slug": self.post.slug})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.post.likes.filter(user=self.user).exists())
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.post.likes.filter(user=self.user).exists())
