from typing import TYPE_CHECKING

from django.apps import apps
from django.conf import settings
from django.db import models

if TYPE_CHECKING:
    from companies.models import Company, CompanyPaymentInfo
    from payments.orders.models import Order


class OrderSplitManager(models.Manager):
    def create_splits_for_company_and_platform(
        self,
        order: "Order",
        company: "Company",
    ):
        OrderSplit = apps.get_model("orders", "OrderSplit")

        payment_info: CompanyPaymentInfo = company.payment_info
        platform_account_id = settings.PAGBANK_ACCOUNT_ID

        company_amount = payment_info.take_rate
        platform_amount = 100 - company_amount

        OrderSplit.objects.create(
            order=order,
            account_external_id=payment_info.payment_account_id,
            percentage=company_amount,
        )
        OrderSplit.objects.create(
            order=order,
            account_external_id=platform_account_id,
            percentage=platform_amount,
            is_platform=True,
        )
