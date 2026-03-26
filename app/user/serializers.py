"""사용자 인증 관련 직렬화기."""
from __future__ import annotations

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Staff, User


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """이메일 기반으로 JWT를 발급하는 직렬화기."""

    username_field = User.USERNAME_FIELD

    @classmethod
    def get_token(cls, user: User):
        token = super().get_token(user)
        token["username"] = user.username
        token["role"] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["username"] = self.user.username
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
            "riding_since",
            "region",
            "intro",
            "sns_link",
            "profile_image",
        ]
        read_only_fields = ("id", "email")

    def validate_username(self, value: str) -> str:
        username = (value or "").strip()
        if not username:
            raise serializers.ValidationError("username은 비워둘 수 없습니다.")
        exists = (
            User.objects.filter(username__iexact=username)
            .exclude(pk=getattr(self.instance, "pk", None))
            .exists()
        )
        if exists:
            raise serializers.ValidationError("이미 사용 중인 username입니다.")
        return username

    def update(self, instance: User, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class StaffSerializer(serializers.ModelSerializer):
    """운영진 계정 정보를 조회·수정."""

    email = serializers.EmailField(source="user.email", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Staff
        fields = [
            "id",
            "email",
            "username",
            "role",
            "bio",
            "contact_email",
            "permissions",
        ]
        read_only_fields = ("id", "email", "username")

    def update(self, instance: Staff, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class MessageSerializer(serializers.Serializer):
    """응답 메시지 래퍼."""

    message = serializers.CharField()


class GoogleOAuthDataSerializer(serializers.Serializer):
    """Google OAuth 로그인 응답 데이터."""

    refresh = serializers.CharField()
    access = serializers.CharField()
    username = serializers.CharField()
    email = serializers.EmailField()
    role = serializers.CharField()
    is_new = serializers.BooleanField()


class GoogleOAuthResponseSerializer(MessageSerializer):
    """Google OAuth 로그인 응답 래퍼."""

    data = GoogleOAuthDataSerializer()


class UserProfileResponseSerializer(MessageSerializer):
    """내 프로필 응답 래퍼."""

    data = UserProfileSerializer()


class UserProfileStatsSerializer(serializers.Serializer):
    """내 프로필 통계."""

    total = serializers.IntegerField()
    by_status = serializers.DictField(child=serializers.IntegerField())


class UserProfileStatsResponseSerializer(MessageSerializer):
    """프로필 통계 응답 래퍼."""

    data = UserProfileStatsSerializer()


class StaffResponseSerializer(MessageSerializer):
    """운영진 정보 응답 래퍼."""

    data = StaffSerializer()



class PublicUserProfileSerializer(serializers.ModelSerializer):
    """공개용 사용자 프로필."""

    profile_image = serializers.SerializerMethodField()
    username = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "riding_since",
            "intro",
            "region",
            "sns_link",
            "profile_image",
        ]
        read_only_fields = fields

    def get_profile_image(self, obj: User):
        image = getattr(obj, "profile_image", None)
        if not image:
            return None
        return {
            "url": image.url,
            "width": image.width,
            "height": image.height,
        }



class PublicUserProfileResponseSerializer(MessageSerializer):
    """공개 프로필 응답 래퍼."""

    data = PublicUserProfileSerializer()
