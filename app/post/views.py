"""View definitions for the post application."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DetailView, FormView, ListView

from .forms import CommentForm, GearCalculatorForm, SubmissionForm
from .models import Comment, Like, Post, PostStatus, Tag


class PublishedPostQuerysetMixin:
    """Provides queryset limited to published posts for non-staff users."""

    def get_queryset(self):  # type: ignore[override]
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
        tag_slug = self.kwargs.get("slug")
        self.tag = get_object_or_404(Tag, slug=tag_slug)
        base_qs = super().get_queryset()
        return base_qs.filter(tags=self.tag, status=PostStatus.PUBLISHED)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_tag"] = getattr(self, "tag", None)
        return context


class PostDetailView(PublishedPostQuerysetMixin, DetailView):
    template_name = "post/post_detail.html"
    context_object_name = "post"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
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
    """Toggle like state for a post."""

    def post(self, request: HttpRequest, slug: str) -> HttpResponse:
        post = get_object_or_404(Post, slug=slug, status=PostStatus.PUBLISHED)
        like, created = Like.objects.get_or_create(post=post, user=request.user)
        if not created:
            like.delete()
            messages.info(request, "좋아요가 취소되었습니다.")
        else:
            messages.success(request, "이 빌드를 좋아요했습니다!")
        return redirect(post.get_absolute_url())


class SubmissionCreateView(FormView):
    """Public form for build submissions."""

    template_name = "post/submission_form.html"
    form_class = SubmissionForm
    success_url = reverse_lazy("post:submit")

    def form_valid(self, form: SubmissionForm) -> HttpResponse:
        form.save()
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
        results = form.calculate()
        messages.success(self.request, "기어비 계산이 완료되었습니다.")
        context = self.get_context_data(form=form, results=results)
        return self.render_to_response(context)
