"""사용자 인증과 프로필 관련 뷰를 정의합니다."""
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View, generic

from app.post.models import Post
from app.submission.forms import SubmissionForm
from app.submission.models import Submission, SubmissionStatus

from .forms import SignupForm


class CustomLoginView(LoginView):
    """권한에 맞는 기본 페이지로 보내는 로그인 뷰입니다."""

    template_name = "user/login.html"

    def get_success_url(self):
        """next 값이 있으면 그대로, 없으면 권한에 맞는 기본 경로로 돌려줍니다."""
        redirect_to = self.get_redirect_url()
        if redirect_to:
            return redirect_to
        if self.request.user.is_superuser:
            return reverse("user:admin_dashboard")
        return reverse("post:list")


class ProfileView(LoginRequiredMixin, generic.TemplateView):
    template_name = "user/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "마이페이지"
        submissions = (
            Submission.objects.filter(user=self.request.user)
            .select_related("bike", "bike__spec")
            .order_by("-created_at")
        )
        context["submissions"] = submissions
        context["submission_status"] = SubmissionStatus
        return context


class SignupView(generic.FormView):
    template_name = "user/signup.html"
    form_class = SignupForm
    success_url = reverse_lazy("post:list")

    def form_valid(self, form: SignupForm):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)


class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, generic.TemplateView):
    """슈퍼유저 전용 대시보드 화면입니다."""

    template_name = "user/admin_dashboard.html"

    def test_func(self):
        """요청 사용자가 슈퍼유저인지 확인합니다."""
        return self.request.user.is_superuser

    def handle_no_permission(self):
        """권한이 없으면 게시판으로, 비로그인이라면 기본 동작을 따릅니다."""
        if self.request.user.is_authenticated:
            return redirect("post:list")
        return super().handle_no_permission()

    def get_context_data(self, **kwargs):
        """최근 신청과 게시글 요약 정보를 채워 넣습니다."""
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


class LogoutRedirectView(LoginRequiredMixin, View):
    """로그아웃하고 홈으로 돌려보내는 뷰입니다."""

    def dispatch(self, request, *args, **kwargs):
        """요청 방식을 가리지 않고 로그아웃한 뒤 홈으로 보냅니다."""
        logout(request)
        return redirect("post:list")


class AdminSubmissionDetailView(LoginRequiredMixin, UserPassesTestMixin, generic.DetailView):
    """신청서를 열람하고 상태를 바꾸는 관리자 뷰입니다."""

    model = Submission
    template_name = "user/admin_submission_detail.html"
    context_object_name = "submission"

    def test_func(self):
        """요청 사용자가 슈퍼유저인지 확인합니다."""
        return self.request.user.is_superuser

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


class SubmissionUpdateView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    """회원이 본인의 소개 신청서를 다시 제출할 때 쓰는 뷰입니다."""

    model = Submission
    form_class = SubmissionForm
    template_name = "user/submission_edit.html"
    success_url = reverse_lazy("user:profile")

    editable_statuses = {
        SubmissionStatus.SUBMITTED,
        SubmissionStatus.IN_REVIEW,
        SubmissionStatus.REJECTED,
    }

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        self._cached_submission = obj
        return obj

    def test_func(self):
        submission = getattr(self, "_cached_submission", None)
        if submission is None:
            submission = self.get_object()
        return (
            submission.user == self.request.user
            and submission.status in self.editable_statuses
        )

    def form_valid(self, form: SubmissionForm):
        form.instance.user = self.request.user
        form.instance.status = SubmissionStatus.SUBMITTED
        form.instance.rejection_reason = ""
        form.instance.reviewer = None
        form.instance.reviewed_at = None
        submission: Submission = form.save(commit=True)
        self.object = submission
        messages.success(self.request, "소개 신청서를 수정했습니다. 운영자가 다시 확인할 거예요.")
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("user:profile")
