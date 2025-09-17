"""Forms for user registration and profile."""
from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm


class SignupForm(UserCreationForm):
    email = forms.EmailField(label="이메일", required=True)
    nickname = forms.CharField(label="닉네임", required=False)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "nickname", "email")

    def save(self, commit: bool = True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        nickname = self.cleaned_data.get("nickname")
        if nickname:
            user.first_name = nickname
        if commit:
            user.save()
        return user
