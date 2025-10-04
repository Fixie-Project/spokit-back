from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views import generic

from app.post.models import Post
from app.submission.models import Submission, SubmissionStatus


class StaffRequiredMixin(UserPassesTestMixin):
    """스태프 권한 사용자만 접근하도록 제한합니다."""

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_staff

    def handle_no_permission(self):
        # 로그인한 일반 사용자는 홈으로 돌려보내고, 비로그인은 기본 처리에 따릅니다.
        if self.request.user.is_authenticated:
            return redirect("post:list")
        return super().handle_no_permission()


class DashboardView(LoginRequiredMixin, StaffRequiredMixin, generic.TemplateView):
    template_name = "studio/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pending_submissions"] = (
            Submission.objects.filter(status__in=[SubmissionStatus.SUBMITTED, SubmissionStatus.IN_REVIEW])
            .select_related("bike", "bike__spec")
            .order_by("-created_at")[:5]
        )
        context["in_progress_submissions"] = (
            Submission.objects.filter(status=SubmissionStatus.IN_PROGRESS)
            .select_related("bike", "bike__spec")
            .order_by("-reviewed_at", "-created_at")[:5]
        )
        context["recent_posts"] = Post.objects.order_by("-created_at")[:5]
        context["total_pending"] = Submission.objects.filter(
            status__in=[SubmissionStatus.SUBMITTED, SubmissionStatus.IN_REVIEW]
        ).count()
        context["total_in_progress"] = Submission.objects.filter(
            status=SubmissionStatus.IN_PROGRESS
        ).count()
        return context


class SubmissionDetailView(LoginRequiredMixin, StaffRequiredMixin, generic.DetailView):
    template_name = "studio/submission_detail.html"
    model = Submission
    context_object_name = "submission"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        submission = self.object
        if submission.status == SubmissionStatus.SUBMITTED:
            submission.status = SubmissionStatus.IN_REVIEW
            submission.reviewer = request.user
            submission.reviewed_at = timezone.now()
            submission.save(update_fields=["status", "reviewer", "reviewed_at"])
        context = self.get_context_data(object=submission)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        submission = self.get_object()
        action = request.POST.get("action")
        if action == "start_draft":
            submission.status = SubmissionStatus.IN_PROGRESS
            submission.reviewer = request.user
            submission.reviewed_at = submission.reviewed_at or timezone.now()
            submission.save(update_fields=["status", "reviewer", "reviewed_at"])
            messages.success(request, "포스팅 준비를 시작했습니다. 자동 임시저장이 활성화됩니다.")
            if submission.result_post:
                edit_url = f"{reverse('post:edit', kwargs={'slug': submission.result_post.slug})}?submission={submission.pk}"
                return redirect(edit_url)
            create_url = f"{reverse('post:create')}?submission={submission.pk}"
            return redirect(create_url)
        if action == "reject":
            reason = (request.POST.get("rejection_reason") or "").strip()
            if not reason:
                messages.error(request, "반려 사유를 입력해 주세요.")
            else:
                submission.status = SubmissionStatus.REJECTED
                submission.rejection_reason = reason
                submission.result_post = None
                submission.save(update_fields=["status", "rejection_reason", "result_post"])
                messages.success(request, "신청서를 반려했습니다.")
        return redirect(self.request.path)
