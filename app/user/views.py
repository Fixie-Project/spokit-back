"""사용자 인증과 프로필 관련 뷰를 정의합니다."""
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views import View, generic

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
        if self.request.user.is_staff:
            return reverse("studio:dashboard")
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


class LogoutRedirectView(LoginRequiredMixin, View):
    """로그아웃하고 홈으로 돌려보내는 뷰입니다."""

    def dispatch(self, request, *args, **kwargs):
        """요청 방식을 가리지 않고 로그아웃한 뒤 홈으로 보냅니다."""
        logout(request)
        return redirect("post:list")


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
