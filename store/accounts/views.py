from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import IntegrityError, transaction

from .models import User
from .otp import OTPError, SMSSendError, send_otp
from .serializers import SendOTPSerializer, UserSerializer, VerifyOTPSerializer


class SendOTPView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        s = SendOTPSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        phone = s.validated_data["phone"]

        try:
            send_otp(phone)
        except SMSSendError as e:
            return Response({"detail": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except OTPError as e:
            return Response({"detail": str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        return Response({
            "detail": "کد ارسال شد.",
            "is_new_user": not User.objects.filter(phone=phone).exists(),
            "expires_in": settings.OTP_EXPIRE_SECONDS,
        })


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        s = VerifyOTPSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data

        user = data["user"]
        created = user is None
        if created:
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        phone=data["phone"],
                        first_name=data["first_name"].strip(),
                        last_name=data["last_name"].strip(),
                    )
            except IntegrityError:
                # درخواست هم‌زمان دیگری کاربر را ساخته است
                user = User.objects.get(phone=data["phone"])
                created = False

        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
            "created": created,
        })

