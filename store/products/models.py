from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models import Q


class Category(models.Model):
    name = models.CharField("نام", max_length=100)
    slug = models.SlugField("اسلاگ", max_length=120, unique=True, allow_unicode=True)
    parent = models.ForeignKey(
        "self", verbose_name="دسته والد", null=True, blank=True,
        on_delete=models.PROTECT, related_name="children",
    )
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"
        ordering = ("name",)

    def __str__(self):
        return f"{self.parent} / {self.name}" if self.parent else self.name


class Color(models.Model):
    name = models.CharField("نام", max_length=50, unique=True)
    hex_code = models.CharField("کد رنگ", max_length=7, help_text="مثال: #000000")

    class Meta:
        verbose_name = "رنگ"
        verbose_name_plural = "رنگ‌ها"

    def __str__(self):
        return self.name


class Size(models.Model):
    name = models.CharField("نام", max_length=20, unique=True)
    order = models.PositiveSmallIntegerField("ترتیب نمایش", default=0)

    class Meta:
        verbose_name = "سایز"
        verbose_name_plural = "سایزها"
        ordering = ("order", "name")

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category, verbose_name="دسته‌بندی",
        on_delete=models.PROTECT, related_name="products",
    )
    name = models.CharField("نام", max_length=200)
    slug = models.SlugField("اسلاگ", max_length=220, unique=True, allow_unicode=True)
    description = models.TextField("توضیحات (شامل برند)", blank=True)
    price = models.PositiveIntegerField("قیمت پایه (تومان)")
    discount_percent = models.PositiveSmallIntegerField(
        "درصد تخفیف", default=0, validators=[MaxValueValidator(100)],
    )
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField("تاریخ ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین ویرایش", auto_now=True)

    class Meta:
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["category", "is_active"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(discount_percent__gte=0, discount_percent__lte=100),
                name="product_discount_0_100",
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def has_discount(self):
        return self.discount_percent > 0

    @property
    def final_price(self):
        return self.price - (self.price * self.discount_percent // 100)


class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product, verbose_name="محصول",
        on_delete=models.CASCADE, related_name="variants",
    )
    color = models.ForeignKey(Color, verbose_name="رنگ", on_delete=models.PROTECT)
    size = models.ForeignKey(Size, verbose_name="سایز", on_delete=models.PROTECT)
    stock = models.PositiveIntegerField("موجودی", default=0)
    sku = models.CharField("کد انبار (SKU)", max_length=50, unique=True)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "تنوع محصول"
        verbose_name_plural = "تنوع‌های محصول"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "color", "size"],
                name="unique_product_color_size",
            ),
        ]

    def __str__(self):
        return f"{self.product} - {self.color} - {self.size}"

    @property
    def in_stock(self):
        return self.stock > 0


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, verbose_name="محصول",
        on_delete=models.CASCADE, related_name="images",
    )
    color = models.ForeignKey(
        Color, verbose_name="رنگ (اختیاری)", null=True, blank=True,
        on_delete=models.SET_NULL,
    )
    image = models.ImageField("تصویر", upload_to="products/%Y/%m/")
    alt_text = models.CharField("متن جایگزین", max_length=200, blank=True)
    is_main = models.BooleanField("عکس اصلی", default=False)
    order = models.PositiveSmallIntegerField("ترتیب", default=0)

    class Meta:
        verbose_name = "تصویر محصول"
        verbose_name_plural = "تصاویر محصول"
        ordering = ("order",)
        constraints = [
            models.UniqueConstraint(
                fields=["product"],
                condition=Q(is_main=True),
                name="unique_main_image_per_product",
            ),
        ]

    def __str__(self):
        return f"تصویر {self.product}"
