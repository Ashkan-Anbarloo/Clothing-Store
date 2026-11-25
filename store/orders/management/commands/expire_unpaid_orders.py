from django.core.management.base import BaseCommand

from orders.services import expire_unpaid_orders


class Command(BaseCommand):
    help = "سفارش‌های پرداخت‌نشده را منقضی و موجودی را برمی‌گرداند."

    def handle(self, *args, **options):
        count = expire_unpaid_orders()
        self.stdout.write(f"{count} سفارش منقضی شد.")
