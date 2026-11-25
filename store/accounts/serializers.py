from rest_framework import serializers
from django.conf import settings
from .models import User, phone_validator
from .otp import OTPError, verify_otp
from .utils import normalize_phone


class PhoneMixin:
    def validate_phone(self, value):
        value = normalize_phone(value)
        phone_validator(value)
        return value


class SendOTPSerializer(PhoneMixin, serializers.Serializer):
    phone = serializers.CharField()

    def validate_phone(self, value):
        value = super().validate_phone(value)
        if User.objects.filter(phone=value, is_active=False).exists():
            raise serializers.ValidationError("این حساب غیرفعال است.")
        return value

class VerifyOTPSerializer(PhoneMixin, serializers.Serializer):
    phone = serializers.CharField()
    code = serializers.CharField()
    first_name = serializers.CharField(max_length=50, required=False)
    last_name = serializers.CharField(max_length=50, required=False)

    def validate(self, attrs):
        phone = attrs["phone"]
        user = User.objects.filter(phone=phone).first()
        if user is not None and not user.is_active:
            raise serializers.ValidationError({"phone": "این حساب غیرفعال است."})


        # کاربر جدید: نام و نام‌خانوادگی اجباری (قبل از بررسی کد، تا کد نسوزد)
        if user is None:
            errors = {}
            for f in ("first_name", "last_name"):
                if not attrs.get(f, "").strip():
                    errors[f] = "این فیلد برای ثبت‌نام الزامی است."
            if errors:
                raise serializers.ValidationError(errors)

        try:
            verify_otp(phone, attrs["code"])
        except OTPError as e:
            raise serializers.ValidationError({"code": str(e)})

        attrs["user"] = user
        return attrs
    
    def validate_code(self, value):
        value = value.strip()
        length = settings.OTP_LENGTH
        if not (value.isascii() and value.isdigit() and len(value) == length):
            raise serializers.ValidationError(f"کد باید {length} رقم و فقط عدد باشد.")
        return value


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "phone", "first_name", "last_name")
