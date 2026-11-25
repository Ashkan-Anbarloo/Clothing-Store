from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = (
        "variant", "product_name", "color_name", "size_name", "sku",
        "original_price", "discount_percent", "unit_price", "quantity",
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "user", "recipient_name", "status",
                    "total_price", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("order_number", "user__phone", "recipient_name",
                     "recipient_phone", "tracking_code")
    inlines = [OrderItemInline]
    readonly_fields = (
        "order_number", "user", "total_price", "paid_at", "expires_at",
        "created_at", "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
