from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView

from .forms import SubmissionForm
from .models import Submission
from .questions import DEFAULT_QUESTION_VERSION, load_question_set


class SubmissionCreateView(FormView):
    """사용자가 소개 신청서를 제출하는 화면."""

    template_name = "post/submission_form.html"
    form_class = SubmissionForm
    success_url = reverse_lazy("submission:submit")

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if request.method != "GET" and not request.user.is_authenticated:
            return redirect_to_login(next=request.path)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_guard"] = not self.request.user.is_authenticated
        context["story_template_url"] = getattr(settings, "SUBMISSION_STORY_TEMPLATE_URL", "")
        question_set = load_question_set(DEFAULT_QUESTION_VERSION)
        context["question_version"] = question_set.version
        context["question_metadata"] = question_set.metadata
        context["question_groups"] = [
            {
                "key": key,
                "label": question_set.group_labels.get(key, key),
                "questions": group,
            }
            for key, group in question_set.groups.items()
        ]
        return context

    def form_valid(self, form: SubmissionForm) -> HttpResponse:
        form.instance.user = self.request.user
        submission = form.save()
        if submission.bike and submission.bike.owner is None:
            bike = submission.bike
            base_name = bike.name or f"Submission {submission.pk}"
            name = base_name
            counter = 1
            while bike.__class__.objects.filter(owner=self.request.user, name=name).exclude(pk=bike.pk).exists():
                counter += 1
                name = f"{base_name} #{counter}"
            bike.owner = self.request.user
            bike.name = name
            bike.save(update_fields=["owner", "name"])
        messages.success(
            self.request,
            "소개글 신청이 접수되었습니다. 운영자가 검토 후 연락드릴게요!",
        )
        return super().form_valid(form)
