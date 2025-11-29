"""사용자 인증 관련 직렬화기."""
from __future__ import annotations

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User
from .models import Staff


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """이메일 기반으로 JWT를 발급하는 직렬화기."""

    username_field = User.USERNAME_FIELD

    @classmethod
    def get_token(cls, user: User):
        token = super().get_token(user)
        token["nickname"] = user.nickname
        token["role"] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["nickname"] = self.user.nickname
        data["email"] = self.user.email
        data["role"] = self.user.role
        return data


class GoogleOAuthSerializer(serializers.Serializer):
    """구글 OAuth 토큰을 검증하기 위한 직렬화기."""

    id_token = serializers.CharField(write_only=True)

    def validate_id_token(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("id_token 값이 필요합니다.")
        return value


class UserProfileSerializer(serializers.ModelSerializer):
    """로그인 사용자의 프로필 정보를 조회/수정."""

    email = serializers.EmailField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "is_username_public",
            "nickname",
            "region",
            "intro",
            "sns_link",
            "profile_image",
        ]
        read_only_fields = ("id", "email")

    def validate_nickname(self, value: str) -> str:
        nickname = value.strip()
        if not nickname:
            raise serializers.ValidationError("닉네임을 입력해 주세요.")
        user = self.instance
        if user and user.nickname == nickname:
            return nickname
        if User.objects.filter(nickname=nickname).exists():
            raise serializers.ValidationError("이미 사용 중인 닉네임입니다.")
        return nickname

    def update(self, instance: User, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class StaffSerializer(serializers.ModelSerializer):
    """운영진 계정 정보를 조회·수정."""

    email = serializers.EmailField(source="user.email", read_only=True)
    nickname = serializers.CharField(source="user.nickname", read_only=True)

    class Meta:
        model = Staff
        fields = [
            "id",
            "email",
            "nickname",
            "role",
            "bio",
            "contact_email",
            "permissions",
        ]
        read_only_fields = ("id", "email", "nickname")

    def update(self, instance: Staff, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance
