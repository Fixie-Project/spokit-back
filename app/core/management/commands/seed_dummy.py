"""Seed dummy data for frontend collaboration."""
from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from typing import Iterable

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from app.bike.models import Bike, BikeBuild, BuildImage, BikeBuildLike, FrameType
from app.core.models import BaseImage
from app.post.models import (
    Comment,
    Like,
    Post,
    PostImage,
    PostImagePurpose,
    PostStatus,
    Tag,
)
from app.submission.models import (
    Submission,
    SubmissionImage,
    SubmissionImagePurpose,
    SubmissionRejectionReason,
    SubmissionStatus,
)
from app.submission.services import build_to_snapshot
from app.user.models import Staff, StaffRole, User, UserRole


DEFAULT_USER_COUNT = 20
DEFAULT_POST_COUNT = 5
DEFAULT_SUBMISSION_TOTAL = 15


@dataclass(frozen=True)
class SeedCounts:
    users: int
    posts: int
    submissions_total: int


def _make_base_image(rng: random.Random, *, width: int = 1200, height: int = 800) -> BaseImage:
    token = uuid.uuid4().hex[:10]
    return BaseImage.objects.create(
        url=f"https://picsum.photos/seed/{token}/{width}/{height}",
        s3_key=f"dummy/{token}.jpg",
        width=width,
        height=height,
        filesize=rng.randint(120_000, 480_000),
    )


def _sample_unique(rng: random.Random, source: list, count: int):
    if not source or count <= 0:
        return []
    count = min(count, len(source))
    return rng.sample(source, count)


class Command(BaseCommand):
    help = "Seed dummy data for frontend collaboration."

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
        parser.add_argument("--reset", action="store_true", help="Delete existing data before seeding")
        parser.add_argument("--users", type=int, default=DEFAULT_USER_COUNT, help="User count (default: 20)")
        parser.add_argument("--posts", type=int, default=DEFAULT_POST_COUNT, help="Post count (default: 5)")
        parser.add_argument(
            "--submissions",
            type=int,
            default=DEFAULT_SUBMISSION_TOTAL,
            help="Total submissions (default: 15)",
        )

    def handle(self, *args, **options):
        rng = random.Random(options["seed"])
        counts = SeedCounts(
            users=options["users"],
            posts=options["posts"],
            submissions_total=options["submissions"],
        )
        run_id = timezone.now().strftime("%Y%m%d%H%M%S")

        if options["reset"]:
            self._reset_data()

        with transaction.atomic():
            tags = self._ensure_tags()
            staff_users = self._create_staff(rng, run_id)
            users = self._create_users(rng, run_id, counts.users)
            bikes, builds = self._create_bikes_and_builds(rng, users)
            builds = self._ensure_min_builds(rng, users, bikes, builds, minimum=2)
            submissions = self._create_submissions(
                rng,
                users,
                builds,
                total=counts.submissions_total,
            )
            posts = self._create_posts(
                rng,
                staff_users,
                users,
                builds,
                submissions,
                tags,
                total=counts.posts,
            )
            self._create_post_engagement(rng, users, posts)
            self._create_build_likes(rng, users, builds)

        self.stdout.write(self.style.SUCCESS("Dummy data seeded."))
        self.stdout.write(
            f"- users: {len(users)} | bikes: {len(bikes)} | builds: {len(builds)}"
        )
        self.stdout.write(f"- submissions: {len(submissions)} | posts: {len(posts)}")

    def _reset_data(self):
        PostImage.objects.all().delete()
        Comment.objects.all().delete()
        Like.objects.all().delete()
        Post.objects.all().delete()
        Tag.objects.all().delete()

        SubmissionImage.objects.all().delete()
        Submission.objects.all().delete()

        BikeBuildLike.objects.all().delete()
        BuildImage.objects.all().delete()
        BikeBuild.objects.all().delete()
        Bike.objects.all().delete()

        Staff.objects.all().delete()
        User.objects.all().delete()
        BaseImage.objects.all().delete()

    def _ensure_tags(self) -> list[Tag]:
        names = [
            "fixed-gear",
            "street",
            "track",
            "custom",
            "archive",
            "interview",
            "build",
            "style",
        ]
        tags = []
        for name in names:
            tag, _ = Tag.objects.get_or_create(name=name)
            tags.append(tag)
        return tags

    def _create_staff(self, rng: random.Random, run_id: str) -> list[Staff]:
        staff_profiles: list[Staff] = []
        for role in (StaffRole.ADMIN, StaffRole.EDITOR):
            email = f"{role.lower()}_{run_id}@dummy.spokit"
            user = User.objects.create_user(
                email=email,
                password="password1234",
                username=f"{role.lower()}_{run_id}",
                nickname=f"{role.lower()}_{run_id}",
                role=UserRole.USER,
            )
            profile = Staff.objects.create(
                user=user,
                role=role,
                bio=f"{role.lower()} staff",
                contact_email=email,
                permissions={"can_edit": True},
            )
            staff_profiles.append(profile)
        return staff_profiles

    def _create_users(self, rng: random.Random, run_id: str, count: int) -> list[User]:
        users: list[User] = []
        regions = ["Seoul, South Korea", "Busan, South Korea", "Tokyo, Japan", "Berlin, Germany"]
        for idx in range(1, count + 1):
            profile_image = _make_base_image(rng, width=400, height=400)
            username = f"dummy_{idx:02d}_{run_id}"
            user = User.objects.create_user(
                email=f"{username}@dummy.spokit",
                password="password1234",
                username=username,
                nickname=username,
                riding_since=rng.randint(2008, 2024),
                region=rng.choice(regions),
                intro="픽시 라이더 더미 프로필입니다.",
                sns_link="https://instagram.com/spokit",
                profile_image=profile_image,
            )
            users.append(user)
        return users

    def _create_bikes_and_builds(
        self, rng: random.Random, users: list[User]
    ) -> tuple[list[Bike], list[BikeBuild]]:
        frame_names = [
            "Cinelli Mash Histogram",
            "Engine 11 Vortex",
            "Dosnoventa Detroit",
            "Affinity Lo Pro",
            "Mash Steel",
            "Leader 725",
            "Colossi LowPro",
        ]
        components_pool = {
            "frame_setup": ["Columbus fork", "Chromoly stem", "Alloy seatpost"],
            "wheel": ["H+Son Archetype", "Phil Wood hubs", "DT Swiss"],
            "cockpit": ["Nitto B123", "Thomson stem", "Ritchey bars"],
            "drivetrain": ["Miche Primato", "Omnium crank", "17T cog"],
            "seat": ["Brooks C15", "Fizik Arione", "Selle Italia"],
            "brake": ["Tektro R540", "Dia-Compe", "Sram brake"],
            "etc": ["Garmin mount", "Sugino bolts", "Izumi chain"],
        }

        bikes: list[Bike] = []
        builds: list[BikeBuild] = []

        for user in users:
            bike_count = rng.randint(0, 4)
            for idx in range(bike_count):
                main_image = _make_base_image(rng)
                bike = Bike.objects.create(
                    owner=user,
                    name=f"{user.username} Frame {idx + 1}",
                    frame_name=rng.choice(frame_names),
                    main_image=main_image,
                    is_posted=rng.choice([True, False]),
                )
                bikes.append(bike)

                build_count = rng.randint(0, 5)
                for build_idx in range(build_count):
                    main_image = _make_base_image(rng)
                    categories = rng.sample(list(components_pool.keys()), k=rng.randint(3, 5))
                    components = {}
                    for category in categories:
                        components[category] = _sample_unique(
                            rng, components_pool[category], rng.randint(1, 2)
                        )
                    build = BikeBuild.objects.create(
                        base_bike=bike,
                        title=f"{bike.frame_name} Build {build_idx + 1}",
                        components=components,
                        note="도시 주행용 세팅",
                        is_public=rng.choice([True, False]),
                        main_image=main_image,
                    )
                    for img_idx in range(rng.randint(1, 3)):
                        image = _make_base_image(rng)
                        BuildImage.objects.create(
                            build=build,
                            image=image,
                            order=img_idx,
                            caption=f"Build shot {img_idx + 1}",
                        )
                    builds.append(build)
        return bikes, builds

    def _ensure_min_builds(
        self,
        rng: random.Random,
        users: list[User],
        bikes: list[Bike],
        builds: list[BikeBuild],
        *,
        minimum: int,
    ) -> list[BikeBuild]:
        if len(builds) >= minimum:
            return builds

        needed = minimum - len(builds)
        for _ in range(needed):
            owner = rng.choice(users)
            if owner.bikes.exists():
                bike = owner.bikes.order_by("?").first()
            else:
                bike = Bike.objects.create(
                    owner=owner,
                    name=f"{owner.username} Frame Extra",
                    frame_name="Cinelli Mash Histogram",
                    main_image=_make_base_image(rng),
                    is_posted=True,
                )
                bikes.append(bike)
            build = BikeBuild.objects.create(
                base_bike=bike,
                title=f"{bike.frame_name} Extra Build",
                components={
                    "frame_setup": ["Chromoly fork"],
                    "wheel": ["H+Son Archetype"],
                    "cockpit": ["Nitto B123"],
                },
                note="추가 빌드",
                is_public=True,
                main_image=_make_base_image(rng),
            )
            BuildImage.objects.create(build=build, image=_make_base_image(rng), order=0)
            builds.append(build)
        return builds

    def _create_submissions(
        self,
        rng: random.Random,
        users: list[User],
        builds: list[BikeBuild],
        *,
        total: int,
    ) -> list[Submission]:
        statuses = [
            SubmissionStatus.DRAFT,
            SubmissionStatus.SUBMITTED,
            SubmissionStatus.IN_REVIEW,
            SubmissionStatus.APPROVED,
            SubmissionStatus.POSTING,
            SubmissionStatus.PUBLISHED,
            SubmissionStatus.REJECTED,
            SubmissionStatus.RESUBMITTED,
        ]
        user_pool = users + users
        rng.shuffle(user_pool)
        selected_users = user_pool[:total]

        submissions: list[Submission] = []
        for idx, user in enumerate(selected_users):
            status = statuses[idx % len(statuses)]
            build = None
            bike = None
            user_builds = list(BikeBuild.objects.filter(base_bike__owner=user))
            if user_builds:
                build = rng.choice(user_builds)
                bike = build.base_bike

            story_blocks = [
                {
                    "question_id": "intro_1",
                    "question_text": "픽시를 타기 시작한 계기는?",
                    "answer": "친구 소개로 시작했습니다.",
                    "images": [f"https://picsum.photos/seed/story-{idx}-1/800/600"],
                },
                {
                    "question_id": "prod_1",
                    "question_text": "조립 컨셉은?",
                    "answer": "도심 라이딩에 맞춘 세팅.",
                    "images": [f"https://picsum.photos/seed/story-{idx}-2/800/600"],
                },
                {
                    "question_id": "outro_1",
                    "question_text": "마무리 한마디?",
                    "answer": "즐겁게 달립니다.",
                },
            ]

            if build:
                build_snapshot = build_to_snapshot(build)
            else:
                build_snapshot = {
                    "bike": {"id": str(uuid.uuid4()), "name": "", "frame_name": "Unknown Frame"},
                    "build": {
                        "id": str(uuid.uuid4()),
                        "title": "Snapshot Build",
                        "components": {"frame_setup": ["Basic frame"], "wheel": ["Basic wheel"], "cockpit": ["Basic bar"]},
                        "note": "스냅샷 전용",
                        "is_public": True,
                        "main_image": {
                            "id": str(uuid.uuid4()),
                            "url": "https://picsum.photos/seed/snapshot/800/600",
                            "width": 800,
                            "height": 600,
                        },
                        "images": [],
                    },
                }

            title = f"{user.username} - {build.title if build else '내 빌드'}"
            submission = Submission.objects.create(
                user=user,
                bike=bike,
                build=build,
                title=title,
                build_snapshot=build_snapshot,
                story_blocks=story_blocks,
                status=status,
                reason_code=(
                    SubmissionRejectionReason.CONTENT_INCOMPLETE
                    if status == SubmissionStatus.REJECTED
                    else ""
                ),
                reason_detail=(
                    "콘텐츠 보완이 필요합니다."
                    if status == SubmissionStatus.REJECTED
                    else ""
                ),
            )
            SubmissionImage.objects.create(
                submission=submission,
                purpose=SubmissionImagePurpose.STORY,
                order=0,
                caption="스토리 이미지",
                url=f"https://picsum.photos/seed/submission-{idx}/800/600",
                s3_key=f"dummy/submission-{idx}.jpg",
                width=800,
                height=600,
                filesize=rng.randint(120_000, 480_000),
            )
            submissions.append(submission)
        return submissions

    def _create_posts(
        self,
        rng: random.Random,
        staff_users: list[Staff],
        users: list[User],
        builds: list[BikeBuild],
        submissions: list[Submission],
        tags: list[Tag],
        *,
        total: int,
    ) -> list[Post]:
        linked_submissions = [s for s in submissions if s.build_id and s.bike_id]
        rng.shuffle(linked_submissions)
        linked_submissions = linked_submissions[:2]

        posts: list[Post] = []
        for idx in range(total):
            staff = rng.choice(staff_users)
            use_submission = idx < len(linked_submissions)
            if use_submission:
                submission = linked_submissions[idx]
                build = submission.build
                bike = submission.bike
                rider = submission.user
                build_snapshot = submission.build_snapshot
                story_snapshot = submission.story_blocks
                rider_snapshot = submission.rider_snapshot
                main_title = submission.title
            else:
                submission = None
                build = rng.choice(builds)
                bike = build.base_bike
                rider = bike.owner
                build_snapshot = build_to_snapshot(build)
                story_snapshot = []
                rider_snapshot = submission.rider_snapshot if submission else {}
                main_title = f"{bike.frame_name} 이야기 {idx + 1}"

            content_md = "도시 라이딩과 커스텀의 기록."
            content_html = "<p>도시 라이딩과 커스텀의 기록.</p>"
            content_json = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": content_md}]}]}

            slug_base = slugify(main_title) or f"post-{idx}"
            slug = f"{slug_base}-{uuid.uuid4().hex[:6]}"

            status = PostStatus.PUBLISHED if idx < 3 else PostStatus.DRAFT

            post = Post.objects.create(
                author=staff,
                submission=submission,
                bike=bike,
                build=build,
                build_snapshot=build_snapshot,
                story_snapshot=story_snapshot,
                rider=rider,
                rider_snapshot=rider_snapshot,
                main_title=main_title,
                content_md=content_md,
                content_html=content_html,
                content_json=content_json,
                frame_brand=bike.frame_name,
                frame_type=rng.choice([ft.value for ft in FrameType]),
                slug=slug,
                status=status,
                is_editor_pick=rng.choice([True, False]),
            )
            post.tags.set(_sample_unique(rng, tags, rng.randint(1, 3)))

            # images (thumbnail + body)
            PostImage.objects.create(
                post=post,
                purpose=PostImagePurpose.THUMBNAIL,
                order=0,
                caption="썸네일",
                url=f"https://picsum.photos/seed/post-{idx}-thumb/800/600",
                s3_key=f"dummy/post-{idx}-thumb.jpg",
                width=800,
                height=600,
                filesize=rng.randint(120_000, 480_000),
            )
            PostImage.objects.create(
                post=post,
                purpose=PostImagePurpose.BODY,
                order=1,
                caption="본문 이미지",
                url=f"https://picsum.photos/seed/post-{idx}-body/1200/800",
                s3_key=f"dummy/post-{idx}-body.jpg",
                width=1200,
                height=800,
                filesize=rng.randint(120_000, 480_000),
            )
            posts.append(post)
        return posts

    def _create_post_engagement(
        self, rng: random.Random, users: list[User], posts: Iterable[Post]
    ) -> None:
        user_list = list(users)
        for post in posts:
            like_users = _sample_unique(rng, user_list, rng.randint(0, min(8, len(user_list))))
            Like.objects.bulk_create(
                [Like(post=post, user=user) for user in like_users],
                ignore_conflicts=True,
            )

            comment_count = rng.randint(0, min(5, len(user_list)))
            comments = []
            for idx in range(comment_count):
                commenter = rng.choice(user_list)
                comments.append(
                    Comment(
                        post=post,
                        user=commenter,
                        content=f"멋진 포스트네요! ({idx + 1})",
                    )
                )
            if comments:
                Comment.objects.bulk_create(comments)

    def _create_build_likes(
        self, rng: random.Random, users: list[User], builds: Iterable[BikeBuild]
    ) -> None:
        user_list = list(users)
        for build in builds:
            like_users = _sample_unique(rng, user_list, rng.randint(0, min(6, len(user_list))))
            BikeBuildLike.objects.bulk_create(
                [BikeBuildLike(build=build, user=user) for user in like_users],
                ignore_conflicts=True,
            )
