"""Views related to authentication and user profiles."""
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views import generic

from .forms import SignupForm


class ProfileView(LoginRequiredMixin, generic.TemplateView):
    template_name = "user/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "내 프로필"
        return context


class SignupView(generic.FormView):
    template_name = "user/signup.html"
    form_class = SignupForm
    success_url = reverse_lazy("post:list")

    def form_valid(self, form: SignupForm):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)
