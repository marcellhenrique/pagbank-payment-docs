import nested_admin
from django.contrib import admin

from payments.orders.models import (
    Order,
    OrderCharge,
    OrderChargePaymentMethod,
    OrderChargePaymentMethodCard,
    OrderItem,
    OrderSplit,
    Phone,
)


class PhoneInline(nested_admin.NestedTabularInline):
    model = Phone
    extra = 0


class OrderItemInline(nested_admin.NestedTabularInline):
    model = OrderItem
    extra = 0


class OrderChargePaymentMethodCardInline(
    nested_admin.NestedStackedInline,
):
    model = OrderChargePaymentMethodCard
    extra = 0


class OrderChargePaymentMethodInline(
    nested_admin.NestedStackedInline,
):
    model = OrderChargePaymentMethod
    extra = 0

    inlines = [OrderChargePaymentMethodCardInline]


class OrderSplitInline(
    nested_admin.NestedStackedInline,
):
    model = OrderSplit
    extra = 0


class OrderChargeInline(nested_admin.NestedStackedInline):
    model = OrderCharge
    extra = 0

    inlines = [OrderChargePaymentMethodInline]


class OrderAdmin(nested_admin.NestedModelAdmin):
    list_display = ("reference_id", "created", "payment_gateway")

    search_fields = ("reference_id", "customer__name")
    inlines = [OrderItemInline, OrderChargeInline, OrderSplitInline]


admin.site.register(Order, OrderAdmin)
