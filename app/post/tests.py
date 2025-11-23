"""Basic smoke tests for post interactions."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from app.bike.models import Bike, BikeBuild, FrameType

from app.submission.models import Submission
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
            story_snapshot=[{"question_id": "q1", "answer": "a1"}],
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
        self.assertEqual(response.status_code, 201)
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

    def test_view_count_increments_on_detail(self) -> None:
        detail_url = reverse("post-detail", kwargs={"slug": self.post.slug})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["view_count"], 1)
        self.post.refresh_from_db(fields=["view_count"])
        self.assertEqual(self.post.view_count, 1)

        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["view_count"], 2)
        self.post.refresh_from_db(fields=["view_count"])
        self.assertEqual(self.post.view_count, 2)

    def test_detail_returns_comment_count_and_like_flag(self) -> None:
        Comment.objects.create(post=self.post, user=self.user, content="첫 댓글")
        detail_url = reverse("post-detail", kwargs={"slug": self.post.slug})

        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["comment_count"], 1)
        self.assertFalse(data["is_liked"])

        self.client.login(username="tester@example.com", password="secret123")
        like_url = reverse("post:like", kwargs={"slug": self.post.slug})
        self.client.post(like_url)

        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["comment_count"], 1)
        self.assertTrue(data["is_liked"])

    def test_editor_pick_flag_in_serializer(self) -> None:
        detail_url = reverse("post-detail", kwargs={"slug": self.post.slug})
        response = self.client.get(detail_url)
        self.assertFalse(response.json()["is_editor_pick"])

        self.post.is_editor_pick = True
        self.post.save(update_fields=["is_editor_pick"])

        response = self.client.get(detail_url)
        self.assertTrue(response.json()["is_editor_pick"])

    def test_post_search_query_filters_results(self) -> None:
        Post.objects.create(
            bike=self.bike,
            build=self.build,
            build_snapshot={"frame": "Affinity"},
            story_snapshot=[],
            main_title="숨은 글",
            sub_title="비공개",
            content_md="",
            content_html="<p>내용</p>",
            content_json={"type": "doc", "content": []},
            frame_brand="Hidden",
            frame_type=FrameType.ALLOY,
            slug="hidden-post",
            status=PostStatus.DRAFT,
        )

        response = self.client.get("/api/posts/?q=첫")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["slug"], self.post.slug)

    def test_sync_snapshots_from_submission(self) -> None:
        submission = Submission.objects.create(
            user=self.user,
            bike=self.bike,
            build=self.build,
            title="Submission",
            build_snapshot={"frame": "Submission Frame"},
            story_blocks=[{"question_id": "q1", "answer": "story"}],
        )
        post = Post.objects.create(
            bike=self.bike,
            build=self.build,
            submission=submission,
            build_snapshot={},
            story_snapshot=[],
            main_title="Snap",
            sub_title="",
            content_md="",
            content_html="<p></p>",
            content_json={"type": "doc", "content": []},
            frame_brand="Brand",
            frame_type=FrameType.ALLOY,
            slug="snap-test",
            status=PostStatus.DRAFT,
        )

        changed = post.sync_snapshots_from_submission(force=True)
        self.assertTrue(changed)
        self.assertEqual(post.build_snapshot, submission.build_snapshot)
        self.assertEqual(post.story_snapshot, submission.story_blocks)
