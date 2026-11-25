from collections import defaultdict
from datetime import timedelta

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from products.models import ProductVariant

from .models import Order, OrderItem

PAYMENT_TIMEOUT_MINUTES = 30

import logging
logger = logging.getLogger(__name__)


class OrderError(Exception):
    """خطایی که پیامش برای کاربر قابل نمایش است."""


@transaction.atomic
def create_order(user, items, shipping):
    """
    items: لیست (variant_id, quantity)
    shipping: دیکشنری با کلیدهای recipient_name, recipient_phone,
              province, city, address, postal_code
    """
    # ادغام آیتم‌های تکراری
    merged = defaultdict(int)
    for variant_id, qty in items:
        if qty < 1:
            raise OrderError("تعداد باید حداقل ۱ باشد.")
        merged[variant_id] += qty
    if not merged:
        raise OrderError("سبد سفارش خالی است.")

    # مرتب‌سازی ثابت برای جلوگیری از بن‌بست (deadlock)
    variant_ids = sorted(merged)
    variants = {
        v.pk: v
        for v in ProductVariant.objects.select_related(
            "product", "color", "size"
        ).filter(pk__in=variant_ids)
    }
    if len(variants) != len(variant_ids):
        raise OrderError("یکی از کالاها پیدا نشد.")

    order = Order.objects.create(
        user=user,
        expires_at=timezone.now() + timedelta(minutes=PAYMENT_TIMEOUT_MINUTES),
        **shipping,
    )

    total = 0
    for variant_id in variant_ids:
        variant = variants[variant_id]
        qty = merged[variant_id]
        product = variant.product

        if not (variant.is_active and product.is_active):
            raise OrderError(f"«{product.name}» در حال حاضر قابل سفارش نیست.")

        # کم کردن اتمیک: فقط اگر موجودی کافی باشد انجام می‌شود
        updated = ProductVariant.objects.filter(
            pk=variant_id, stock__gte=qty
        ).update(stock=F("stock") - qty)
        if not updated:
            raise OrderError(f"موجودی «{product.name}» کافی نیست.")

        unit_price = product.final_price
        OrderItem.objects.create(
            order=order,
            variant=variant,
            product_name=product.name,
            color_name=variant.color.name,
            size_name=variant.size.name,
            sku=variant.sku,
            original_price=product.price,
            discount_percent=product.discount_percent,
            unit_price=unit_price,
            quantity=qty,
        )
        total += unit_price * qty

    order.total_price = total
    order.order_number = str(100000 + order.pk)
    order.save(update_fields=["total_price", "order_number", "updated_at"])
    return order


@transaction.atomic
def expire_order(order_id):
    """سفارش پرداخت‌نشده را منقضی و موجودی را برمی‌گرداند."""
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status != Order.Status.PENDING:
        return False  # قبلاً پرداخت یا منقضی شده

    for item in order.items.all():
        ProductVariant.objects.filter(pk=item.variant_id).update(
            stock=F("stock") + item.quantity
        )
    order.status = Order.Status.EXPIRED
    order.save(update_fields=["status", "updated_at"])
    return True


@transaction.atomic
def mark_as_paid(order_id):
    """بعد از تأیید پرداخت صدا زده می‌شود (در مرحله‌ی درگاه)."""
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status != Order.Status.PENDING:
        return False
    order.status = Order.Status.PAID
    order.paid_at = timezone.now()
    order.save(update_fields=["status", "paid_at", "updated_at"])
    return True


def expire_unpaid_orders():
    """همه‌ی سفارش‌های منقضی‌شده را رسیدگی می‌کند. تعداد را برمی‌گرداند."""
    ids = Order.objects.filter(
        status=Order.Status.PENDING, expires_at__lt=timezone.now()
    ).values_list("pk", flat=True)

    count = 0
    for pk in list(ids):
        try:
            if expire_order(pk):
                count += 1
        except Exception:
            logger.exception("خطا در منقضی کردن سفارش %s", pk)
    return count
