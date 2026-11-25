from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار پرداخت"
        PAID = "paid", "پرداخت شده"
        PROCESSING = "processing", "در حال آماده‌سازی"
        SHIPPED = "shipped", "ارسال شده"
        DELIVERED = "delivered", "تحویل شده"
        EXPIRED = "expired", "منقضی شده (پرداخت نشد)"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="کاربر",
    )
    order_number = models.CharField(
        "شماره سفارش", max_length=20, unique=True,
        null=True, blank=True, editable=False,
    )
    status = models.CharField(
        "وضعیت", max_length=20,
        choices=Status.choices, default=Status.PENDING,
    )

    # اطلاعات گیرنده و آدرس (هر سفارش آدرس خودش را دارد)
    recipient_name = models.CharField("نام گیرنده", max_length=100)
    recipient_phone = models.CharField(
        "شماره تماس گیرنده", max_length=11,
        validators=[RegexValidator(r"^09\d{9}$", "شماره موبایل معتبر نیست.")],
    )
    province = models.CharField("استان", max_length=50)
    city = models.CharField("شهر", max_length=50)
    address = models.TextField("آدرس کامل")
    postal_code = models.CharField(
        "کد پستی", max_length=10,
        validators=[RegexValidator(r"^\d{10}$", "کد پستی باید ۱۰ رقم باشد.")],
    )

    # مبلغ (تومان). هزینه ارسال را مشتری هنگام تحویل می‌دهد، پس اینجا نیست.
    total_price = models.PositiveBigIntegerField(
        "جمع کل", default=0, validators=[MinValueValidator(0)]
    )

    paid_at = models.DateTimeField("زمان پرداخت", null=True, blank=True)
    expires_at = models.DateTimeField("مهلت پرداخت")
    tracking_code = models.CharField("کد رهگیری پست", max_length=50, blank=True)

    created_at = models.DateTimeField("تاریخ ثبت", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین تغییر", auto_now=True)

    class Meta:
        verbose_name = "سفارش"
        verbose_name_plural = "سفارش‌ها"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("status", "expires_at")),
            models.Index(fields=("user", "-created_at")),
        ]

    def __str__(self):
        return f"سفارش {self.order_number or self.pk}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE,
        related_name="items", verbose_name="سفارش",
    )
    variant = models.ForeignKey(
        "products.ProductVariant", on_delete=models.PROTECT,
        related_name="order_items", verbose_name="تنوع کالا",
    )

    # کپی ثابت (Snapshot) از لحظه خرید
    product_name = models.CharField("نام محصول", max_length=255)
    color_name = models.CharField("رنگ", max_length=50)
    size_name = models.CharField("سایز", max_length=50)
    sku = models.CharField("SKU", max_length=50, blank=True)
    original_price = models.PositiveBigIntegerField("قیمت اصلی واحد")
    discount_percent = models.PositiveSmallIntegerField("درصد تخفیف", default=0)
    unit_price = models.PositiveBigIntegerField("قیمت واحد پس از تخفیف")

    quantity = models.PositiveIntegerField(
        "تعداد", validators=[MinValueValidator(1)]
    )

    class Meta:
        verbose_name = "آیتم سفارش"
        verbose_name_plural = "آیتم‌های سفارش"
        constraints = [
            models.UniqueConstraint(
                fields=("order", "variant"), name="unique_variant_per_order"
            ),
        ]

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"

    @property
    def total_price(self):
        return self.unit_price * self.quantity
