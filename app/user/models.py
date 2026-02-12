"""Spokit 사용자 및 운영진 모델 정의."""
from __future__ import annotations

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import URLValidator
from django.db import models

from app.core.models import BaseModel, BaseImage, TimeStampedModel, UUIDPrimaryKeyModel


class UserRole(models.TextChoices):
    """플랫폼에서 지원하는 사용자 역할."""

    USER = "USER", "사용자"
    EDITOR = "EDITOR", "에디터"
    ADMIN = "ADMIN", "관리자"


class UserManager(BaseUserManager):
    """이메일을 로그인 ID로 사용하는 사용자 매니저."""

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("이메일은 필수 입력 값입니다.")
        email = self.normalize_email(email)
        if not extra_fields.get("username"):
            extra_fields["username"] = email.split("@")[0]
        if not extra_fields.get("nickname"):
            extra_fields["nickname"] = extra_fields["username"]
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("role", UserRole.USER)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRole.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(UUIDPrimaryKeyModel, TimeStampedModel, AbstractBaseUser, PermissionsMixin):
    """이메일을 로그인 ID로 사용하는 메인 사용자 모델."""

    email = models.EmailField(unique=True)
    username = models.CharField(max_length=50)
    nickname = models.CharField(max_length=50, blank=True)
    riding_since = models.PositiveSmallIntegerField(null=True, blank=True)
    region = models.CharField(max_length=50, blank=True)
    intro = models.TextField(blank=True)
    sns_link = models.URLField(blank=True, validators=[URLValidator(schemes=["http", "https"])])
    profile_image = models.ForeignKey(
        BaseImage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="profile_users",
    )
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.USER)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        db_table = "user_user"
        verbose_name = "사용자"
        verbose_name_plural = "사용자"
        indexes = [
            models.Index(fields=["email"], name="user_email_idx"),
            models.Index(fields=["nickname"], name="user_nickname_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - 간단한 표시용 메서드
        return self.username or self.nickname or self.email

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.__class__.objects.normalize_email(self.email)
        if self.nickname:
            self.nickname = self.nickname.strip()
        if self.username:
            self.username = self.username.strip()


class StaffRole(models.TextChoices):
    """운영진에게 부여되는 역할 종류."""

    EDITOR = "EDITOR", "에디터"
    ADMIN = "ADMIN", "관리자"


class Staff(BaseModel):
    """사용자 계정에 연결된 운영진 정보."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="staff_profile",
    )
    role = models.CharField(max_length=20, choices=StaffRole.choices)
    bio = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)
    permissions = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "user_staff"
        verbose_name = "운영진"
        verbose_name_plural = "운영진"

    def __str__(self) -> str:  # pragma: no cover - 간단한 표시용 메서드
        return f"{self.get_role_display()} · {self.user}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._sync_user_role()

    def delete(self, *args, **kwargs):
        user = self.user
        super().delete(*args, **kwargs)
        self._reset_user_role(user)

    def _sync_user_role(self) -> None:
        user = self.user
        target_role = self.role
        if user.role != target_role:
            user.role = target_role
        if not user.is_staff:
            user.is_staff = True
        user.save(update_fields=["role", "is_staff", "updated_at"])

    def _reset_user_role(self, user: User) -> None:
        if user.is_superuser:
            return
        user.role = UserRole.USER
        user.is_staff = False
        user.save(update_fields=["role", "is_staff", "updated_at"])
