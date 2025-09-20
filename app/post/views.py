"""게시글 애플리케이션의 뷰 정의입니다."""
from __future__ import annotations

import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, FormView, ListView, UpdateView

from .forms import CommentForm, GearCalculatorForm, PostForm, SubmissionForm
from .models import Comment, Like, Post, PostStatus, Submission, SubmissionStatus, Tag


class PublishedPostQuerysetMixin:
    """비직원 사용자가 볼 수 있도록 발행된 게시글만 반환합니다."""

    def get_queryset(self):  # type: ignore[override]
        """발행 상태인 게시글을 기본으로 조회합니다."""
        qs = (
            Post.objects.select_related("author")
            .prefetch_related("tags")
            .annotate(like_count=Count("likes"))
        )
        request: HttpRequest = self.request  # type: ignore[attr-defined]
        if request.user.is_staff:
            return qs
        return qs.filter(status=PostStatus.PUBLISHED)


class PostListView(PublishedPostQuerysetMixin, ListView):
    template_name = "post/post_list.html"
    context_object_name = "posts"
    paginate_by = 9

    def get_context_data(self, **kwargs):
        """게시글 목록에 태그와 추천 게시글 정보를 포함합니다."""
        context = super().get_context_data(**kwargs)
        context["tags"] = (
            Tag.objects.annotate(
                post_count=Count(
                    "posts",
                    filter=Q(posts__status=PostStatus.PUBLISHED),
                )
            )
            .filter(post_count__gt=0)
            .order_by("name")
        )
        context["featured"] = (
            self.get_queryset()
            .filter(status=PostStatus.PUBLISHED, featured=True)
            .order_by("-published_at")[:3]
        )
        return context


class TaggedPostListView(PostListView):
    template_name = "post/tagged_list.html"

    def get_queryset(self):  # type: ignore[override]
        """선택된 태그가 붙은 발행 게시글만 가져옵니다."""
        tag_slug = self.kwargs.get("slug")
        self.tag = get_object_or_404(Tag, slug=tag_slug)
        base_qs = super().get_queryset()
        return base_qs.filter(tags=self.tag, status=PostStatus.PUBLISHED)

    def get_context_data(self, **kwargs):
        """현재 선택된 태그 정보를 컨텍스트에 추가합니다."""
        context = super().get_context_data(**kwargs)
        context["current_tag"] = getattr(self, "tag", None)
        return context


class PostDetailView(PublishedPostQuerysetMixin, DetailView):
    template_name = "post/post_detail.html"
    context_object_name = "post"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        """게시글 상세 페이지에 댓글, 좋아요 정보를 채웁니다."""
        context = super().get_context_data(**kwargs)
        post: Post = context["post"]
        if "comment_form" not in context:
            context["comment_form"] = CommentForm()
        context["comments"] = post.comments.filter(is_blocked=False).select_related("user")
        if self.request.user.is_authenticated:
            context["user_liked"] = post.likes.filter(user=self.request.user).exists()
        context["like_count"] = post.likes.count()
        return context

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """인증된 사용자의 댓글 작성 요청을 처리합니다."""
        self.object = self.get_object()
        if not request.user.is_authenticated:
            return redirect_to_login(next=self.object.get_absolute_url())
        form = CommentForm(request.POST)
        if form.is_valid():
            Comment.objects.create(
                post=self.object,
                user=request.user,
                content=form.cleaned_data["content"],
            )
            messages.success(request, "댓글이 등록되었습니다.")
            return redirect(self.object.get_absolute_url())
        context = self.get_context_data(comment_form=form)
        return self.render_to_response(context)


class LikeToggleView(LoginRequiredMixin, View):
    """게시글의 좋아요 상태를 전환합니다."""

    def post(self, request: HttpRequest, slug: str) -> HttpResponse:
        """좋아요를 토글한 후 게시글 상세 페이지로 이동합니다."""
        post = get_object_or_404(Post, slug=slug, status=PostStatus.PUBLISHED)
        like, created = Like.objects.get_or_create(post=post, user=request.user)
        if not created:
            like.delete()
            messages.info(request, "좋아요가 취소되었습니다.")
        else:
            messages.success(request, "이 빌드를 좋아요했습니다!")
        return redirect(post.get_absolute_url())


class SubmissionCreateView(FormView):
    """공개 빌드 제출을 위한 양식입니다."""

    template_name = "post/submission_form.html"
    form_class = SubmissionForm
    success_url = reverse_lazy("post:submit")

    def form_valid(self, form: SubmissionForm) -> HttpResponse:
        """제출된 소개글을 저장하고 안내 메시지를 제공합니다."""
        submission = form.save()
        if self.request.user.is_authenticated:
            submission.user = self.request.user
            submission.save(update_fields=["user"])
        messages.success(
            self.request,
            "소개글 신청이 접수되었습니다. 운영자가 검토 후 연락드릴게요!",
        )
        return super().form_valid(form)


class GearCalculatorView(FormView):
    template_name = "post/gear_calculator.html"
    form_class = GearCalculatorForm
    success_url = reverse_lazy("post:gear_calc")

    def form_valid(self, form: GearCalculatorForm) -> HttpResponse:
        """기어비 계산 결과를 생성해 템플릿에 전달합니다."""
        results = form.calculate()
        messages.success(self.request, "기어비 계산이 완료되었습니다.")
        context = self.get_context_data(form=form, results=results)
        return self.render_to_response(context)


class SubmissionLinkedPostMixin(LoginRequiredMixin, UserPassesTestMixin):
    """슈퍼유저가 신청서와 연동해 게시글을 작성/수정할 때 공통 로직을 제공합니다."""

    template_name = "post/post_form.html"
    form_class = PostForm
    submission: Submission | None = None

    def test_func(self):
        return self.request.user.is_superuser

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        submission_id = request.GET.get("submission") or request.POST.get("submission")
        self.submission = None
        if submission_id:
            self.submission = get_object_or_404(Submission, pk=submission_id)
        return super().dispatch(request, *args, **kwargs)

    def get_submission(self) -> Submission | None:
        if self.submission:
            return self.submission
        obj = getattr(self, "object", None)
        if obj is not None:
            linked = obj.source_submissions.first()
            if linked:
                self.submission = linked
        return self.submission

    def get_initial(self):
        initial = super().get_initial()
        submission = self.get_submission()
        if submission:
            draft = submission.draft_data or {}
            if draft:
                for key in ["title", "slug", "summary", "body", "cover_image", "status", "featured"]:
                    if draft.get(key) is not None:
                        initial[key] = draft.get(key)
                if draft.get("tags"):
                    initial["tags"] = [int(tag_id) for tag_id in draft.get("tags", [])]
            elif not getattr(self, "object", None):
                initial.setdefault("title", f"{submission.submitter_name} 소개")
                if submission.message:
                    initial.setdefault("summary", submission.message[:200])
                    initial.setdefault("body", submission.message)
        return initial

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        submission = self.get_submission()
        if submission:
            draft = submission.draft_data or {}
            if draft.get("tags"):
                tag_ids = [int(tag_id) for tag_id in draft.get("tags", [])]
                form.fields["tags"].initial = tag_ids
        return form

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if hasattr(self, "get_object") and not isinstance(self, CreateView):
            self.object = self.get_object()
        else:
            self.object = None

        form = self.get_form()
        confirmed = request.POST.get("confirm_publish") == "1"
        submission = self.get_submission()

        if not confirmed and not submission and getattr(self, "object", None):
            confirmed = True

        if confirmed:
            if form.is_valid():
                return self.form_valid(form)
            return self.form_invalid(form)

        if form.is_valid():
            if submission:
                self._save_submission_draft(form)
                messages.success(request, "임시저장을 완료했습니다.")
            else:
                messages.info(request, "초안이 저장되었습니다. 게시하려면 최종 확인을 진행해 주세요.")
            return self.render_to_response(self.get_context_data(form=form))
        return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        submission = self.get_submission()
        context["submission"] = submission
        context["is_edit"] = bool(getattr(self, "object", None))
        return context

    def form_valid(self, form: PostForm) -> HttpResponse:
        submission = self.get_submission()
        is_update = form.instance.pk is not None
        if not form.instance.author:
            form.instance.author = self.request.user
        message = "게시글이 업데이트되었습니다." if is_update else "새 게시글이 저장되었습니다."
        response = super().form_valid(form)
        if submission:
            status = (
                SubmissionStatus.PUBLISHED
                if form.cleaned_data.get("status") == PostStatus.PUBLISHED
                else SubmissionStatus.IN_PROGRESS
            )
            submission.status = status
            submission.result_post = self.object
            submission.rejection_reason = ""
            submission.save(update_fields=["status", "result_post", "rejection_reason"])
        messages.success(self.request, message)
        return response

    def _save_submission_draft(self, form: PostForm) -> None:
        submission = self.get_submission()
        if not submission:
            return
        cleaned = form.cleaned_data
        tags = cleaned.get("tags") or []
        if hasattr(tags, "values_list"):
            tag_ids = list(tags.values_list("id", flat=True))
        else:
            tag_ids = [getattr(tag, "pk", tag) for tag in tags]

        draft_data = {
            "title": cleaned.get("title"),
            "slug": cleaned.get("slug"),
            "summary": cleaned.get("summary"),
            "body": cleaned.get("body"),
            "cover_image": cleaned.get("cover_image"),
            "status": cleaned.get("status"),
            "featured": cleaned.get("featured"),
            "tags": tag_ids,
            "saved_at": timezone.now().isoformat(timespec="seconds"),
        }

        submission.draft_data = draft_data
        fields = ["draft_data"]
        if submission.status != SubmissionStatus.IN_PROGRESS:
            submission.status = SubmissionStatus.IN_PROGRESS
            fields.append("status")
        if submission.reviewer is None:
            submission.reviewer = self.request.user
            fields.append("reviewer")
        if submission.reviewed_at is None:
            submission.reviewed_at = timezone.now()
            fields.append("reviewed_at")
        submission.save(update_fields=fields)


class PostCreateView(SubmissionLinkedPostMixin, CreateView):
    """슈퍼유저가 게시글을 신규 작성합니다."""

    model = Post


class PostUpdateView(SubmissionLinkedPostMixin, UpdateView):
    """슈퍼유저가 기존 게시글을 수정합니다."""

    model = Post
    slug_field = "slug"
    slug_url_kwarg = "slug"


class SubmissionDraftAutosaveView(LoginRequiredMixin, UserPassesTestMixin, View):
    """자동 임시저장 요청을 받아 제출서 초안을 기록합니다."""

    def test_func(self):
        return self.request.user.is_superuser

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        try:
            payload = json.loads(request.body.decode("utf-8")) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({"ok": False, "error": "잘못된 요청 형식입니다."}, status=400)

        submission_id = payload.get("submission_id")
        if not submission_id:
            return JsonResponse({"ok": False, "error": "submission_id가 필요합니다."}, status=400)

        submission = get_object_or_404(Submission, pk=submission_id)

        draft_tags = payload.get("tags", []) or []
        try:
            draft_tags = [int(tag) for tag in draft_tags]
        except (TypeError, ValueError):
            draft_tags = []

        draft_data = {
            "title": payload.get("title"),
            "slug": payload.get("slug"),
            "summary": payload.get("summary"),
            "body": payload.get("body"),
            "cover_image": payload.get("cover_image"),
            "status": payload.get("status"),
            "featured": payload.get("featured"),
            "tags": draft_tags,
            "saved_at": timezone.now().isoformat(timespec="seconds"),
        }

        submission.draft_data = draft_data
        fields = ["draft_data"]
        if submission.status != SubmissionStatus.IN_PROGRESS:
            submission.status = SubmissionStatus.IN_PROGRESS
            fields.append("status")
        if submission.reviewer is None:
            submission.reviewer = request.user
            fields.append("reviewer")
        if submission.reviewed_at is None:
            submission.reviewed_at = timezone.now()
            fields.append("reviewed_at")
        submission.save(update_fields=fields)
        return JsonResponse({"ok": True, "saved_at": draft_data["saved_at"]})
