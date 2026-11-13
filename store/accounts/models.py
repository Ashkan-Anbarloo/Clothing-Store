from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.utils import timezone

from .managers import UserManager
from .utils import normalize_phone

phone_validator = RegexValidator(
    regex=r"^09\d{9}$",
    message="شماره موبایل باید با 09 شروع شود و ۱۱ رقم باشد.",
)


class User(AbstractBaseUser, PermissionsMixin):
    phone = models.CharField(
        "شماره موبایل", max_length=11, unique=True, validators=[phone_validator]
    )
    first_name = models.CharField("نام", max_length=50)
    last_name = models.CharField("نام خانوادگی", max_length=50)
    is_active = models.BooleanField("فعال", default=True)
    is_staff = models.BooleanField("دسترسی ادمین", default=False)
    date_joined = models.DateTimeField("تاریخ عضویت", default=timezone.now)
    updated_at = models.DateTimeField("آخرین بروزرسانی", auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"

    def __str__(self):
        return self.phone

    def save(self, *args, **kwargs):
        self.phone = normalize_phone(self.phone)
        super().save(*args, **kwargs)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name
