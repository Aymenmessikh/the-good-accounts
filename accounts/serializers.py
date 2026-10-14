from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth import authenticate, get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Read-only representation of a user (never exposes the password)."""

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "date_joined")
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                lookup="iexact",  # case-insensitive uniqueness
                message="A user with this email already exists.",
            )
        ]
    )
    password = serializers.CharField(
        write_only=True, trim_whitespace=False, style={"input_type": "password"}
    )
    password_confirm = serializers.CharField(
        write_only=True, trim_whitespace=False, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "password", "password_confirm")

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "The two passwords do not match."}
            )

        # Run Django's AUTH_PASSWORD_VALIDATORS (length, common, numeric, similarity).
        # We pass an unsaved user so the "too similar to your email/name" rule works.
        candidate = User(
            email=attrs["email"],
            first_name=attrs["first_name"],
            last_name=attrs["last_name"],
        )
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})

        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        # create_user hashes the password and lowercases the email
        return User.objects.create_user(**validated_data)

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True, trim_whitespace=False, style={"input_type": "password"}
    )

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            email=attrs["email"].lower(),
            password=attrs["password"],
        )
        if user is None:
            # Same message for unknown email, wrong password or inactive account:
            # we never reveal which one it was.
            raise serializers.ValidationError(
                "Invalid email or password.", code="authorization"
            )
        attrs["user"] = user
        return attrs

class ProfileSerializer(serializers.ModelSerializer):
    """The logged-in user's own profile. Only the names can be changed."""

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "date_joined")
        read_only_fields = ("id", "email", "date_joined")

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        write_only=True, trim_whitespace=False, style={"input_type": "password"}
    )
    new_password = serializers.CharField(
        write_only=True, trim_whitespace=False, style={"input_type": "password"}
    )
    new_password_confirm = serializers.CharField(
        write_only=True, trim_whitespace=False, style={"input_type": "password"}
    )

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Your current password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "The two passwords do not match."}
            )
        if attrs["new_password"] == attrs["old_password"]:
            raise serializers.ValidationError(
                {"new_password": "The new password must be different from the current one."}
            )
        user = self.context["request"].user
        try:
            validate_password(attrs["new_password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)})
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        return user