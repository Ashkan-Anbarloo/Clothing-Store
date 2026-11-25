import logging
import secrets

from django.conf import settings
from django.core.cache import cache

from .sms import send_sms

logger = logging.getLogger(__name__)

class OTPError(Exception):
    pass

class SMSSendError(OTPError):
    pass


def _k(kind, phone):
    return f"otp:{kind}:{phone}"


def send_otp(phone):
    # جلوگیری از ارسال پشت‌سرهم
    if not cache.add(_k("cooldown", phone), 1, settings.OTP_RESEND_SECONDS):
        raise OTPError("لطفاً کمی صبر کنید و دوباره تلاش کنید.")

    code = "".join(str(secrets.randbelow(10)) for _ in range(settings.OTP_LENGTH))
    cache.set(_k("code", phone), code, settings.OTP_EXPIRE_SECONDS)
    cache.delete(_k("attempts", phone))

    try:
        send_sms(phone, f"کد ورود شما: {code}")
    except Exception:
        # ارسال ناموفق: قفل و کد را پاک کن تا کاربر بتواند دوباره تلاش کند
        logger.exception("SMS send failed for %s", phone)
        cache.delete(_k("cooldown", phone))
        cache.delete(_k("code", phone))
        raise OTPError("ارسال پیامک ناموفق بود. دوباره تلاش کنید.")


def verify_otp(phone, code):
    saved = cache.get(_k("code", phone))
    if saved is None:
        raise OTPError("کد منقضی شده یا ارسال نشده است.")

    attempts = cache.get(_k("attempts", phone), 0)
    if attempts >= settings.OTP_MAX_ATTEMPTS:
        cache.delete(_k("code", phone))
        raise OTPError("تعداد تلاش‌ها زیاد بود. کد جدید بگیرید.")

    if not secrets.compare_digest(saved, str(code)):
        cache.set(_k("attempts", phone), attempts + 1, settings.OTP_EXPIRE_SECONDS)
        raise OTPError("کد اشتباه است.")

    cache.delete(_k("code", phone))
    cache.delete(_k("attempts", phone))
