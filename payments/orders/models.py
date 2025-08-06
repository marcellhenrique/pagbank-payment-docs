from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel

from payments.integrations.enums import PaymentGatewayIntegrations
from payments.orders.helpers import get_default_qr_code_expiration
from payments.orders.managers import OrderSplitManager


class Address(TimeStampedModel):
    state = models.CharField(_("State"), max_length=255)
    city = models.CharField(_("City"), max_length=255)
    district = models.CharField(_("District"), max_length=255)
    street = models.CharField(_("Street"), max_length=255)
    number = models.CharField(_("Number"), max_length=255)
    zip_code = models.CharField(_("Zip code"), max_length=15)
    additional_info = models.CharField(
        _("Additional info"),
        max_length=255,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-id"]
        verbose_name = _("Address")
        verbose_name_plural = _("Addresses")

    def __str__(self) -> str:
        return (
            f"{self.street} {self.number} - {self.district} - {self.city}/{self.state}"
        )


class Customer(TimeStampedModel):
    external_id = models.CharField(
        _("External id"),
        max_length=255,
        null=True,
        blank=True,
    )
    name = models.CharField(_("Name"), max_length=30)
    email = models.EmailField(_("Email"))
    document = models.CharField(_("Document"), max_length=14)
    address = models.OneToOneField(Address, on_delete=models.PROTECT, null=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = _("Customer")
        verbose_name_plural = _("Customers")

    def __str__(self) -> str:
        return f"{self.name} {self.document}"


class Phone(TimeStampedModel):
    customer = models.OneToOneField(
        Customer,
        on_delete=models.PROTECT,
        related_name="phone",
    )
    country_code = models.CharField(_("Country code"), max_length=3)
    area_code = models.CharField(_("Area code"), max_length=2)
    number = models.CharField(_("Number"), max_length=9)

    class Meta:
        ordering = ["-id"]
        verbose_name = _("Phone")
        verbose_name_plural = _("Phones")

    def __str__(self) -> str:
        return f"{self.country_code} ({self.area_code}) {self.number}"


class Order(TimeStampedModel):
    reference_id = models.UUIDField(
        _("Reference id"),
        default=uuid4,
        unique=True,
        primary_key=True,
    )
    external_id = models.CharField(
        _("External id"),
        max_length=255,
        null=True,
        blank=True,
    )

    customer = models.OneToOneField(
        Customer,
        on_delete=models.PROTECT,
    )
    payment_gateway = models.CharField(
        "Payment gateway",
        max_length=64,
        choices=PaymentGatewayIntegrations.choices,
    )

    class Meta:
        ordering = ["-created"]
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    def __str__(self) -> str:
        return f"{self.reference_id}"


class OrderItem(TimeStampedModel):
    reference_id = models.UUIDField(
        _("Reference id"),
        default=uuid4,
        unique=True,
        primary_key=True,
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name="items",
    )
    name = models.CharField(_("Name"))
    quantity = models.PositiveSmallIntegerField(_("Quantity"))
    unit_amount = models.PositiveBigIntegerField(_("Unit amount"))

    class Meta:
        ordering = ["-created"]
        verbose_name = _("Order item")
        verbose_name_plural = _("Order items")

    def __str__(self) -> str:
        return f"{self.name} - {self.quantity}"


class OrderCharge(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", _("pending")
        PROCESSING = "PROCESSING", _("processing")
        FAILED = "FAILED", _("failed")
        CREATED = "CREATED", _("created")
        CANCELED = "CANCELED", _("canceled")
        AUTHORIZED = "AUTHORIZED", _("authorized")
        DECLINED = "DECLINED", _("declined")
        PAID = "PAID", _("paid")

    class CancelStatus(models.TextChoices):
        NOT_CANCELED = "NOT_CANCELED", _("not canceled")
        PENDING = "PENDING", _("pending")
        PROCESSING = "PROCESSING", _("processing")
        CANCELED = "CANCELED", _("canceled")
        FAILED = "FAILED", _("failed")

    reference_id = models.UUIDField(
        _("Reference id"),
        default=uuid4,
        unique=True,
        primary_key=True,
    )
    external_id = models.CharField(
        _("External id"),
        max_length=255,
        null=True,
        blank=True,
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name="charges",
    )
    description = models.CharField(_("Description"), max_length=64)
    value = models.PositiveBigIntegerField(_("Value"))
    currency = models.CharField(_("Currency"))

    status = models.CharField(
        _("Status"),
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    cancel_status = models.CharField(
        _("Cancel status"),
        max_length=12,
        choices=CancelStatus.choices,
        default=CancelStatus.NOT_CANCELED,
    )

    paid_at = models.DateTimeField(_("Paid at"), null=True, blank=True)
    canceled_at = models.DateTimeField(_("Canceled at"), null=True, blank=True)

    class Meta:
        ordering = ["-created"]
        verbose_name = _("Order charge")
        verbose_name_plural = _("Order charges")

    def __str__(self) -> str:
        return f"{self.reference_id}: {self.description}"

    def save(
        self,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ) -> None:
        if not self.description:
            self.description = self.default_description

        return super().save(force_insert, force_update, using, update_fields)

    @property
    def default_description(self):
        return settings.PROJECT_NAME


class OrderChargePaymentMethod(models.Model):
    class Types(models.TextChoices):
        CREDIT_CARD = "CREDIT_CARD", _("Credit card")
        PIX = "PIX", _("Pix")

    class OperationType(models.TextChoices):
        AUTH_AND_CAPTURE = "AUTH_AND_CAPTURE"

    charge = models.OneToOneField(
        OrderCharge,
        on_delete=models.PROTECT,
        related_name="payment_method",
    )
    type = models.CharField(_("Type"), choices=Types.choices, max_length=11)
    installments = models.PositiveSmallIntegerField(_("Installments"), null=True)
    operation_type = models.CharField(
        _("Operation type"),
        choices=OperationType.choices,
        max_length=16,
        null=True,
    )

    description = models.CharField(_("Description"), max_length=22)

    class Meta:
        ordering = ["-id"]
        verbose_name = _("Charge payment method")
        verbose_name_plural = _("Charge payment methods")

    def __str__(self) -> str:
        return f"{self.charge} - {self.type}"

    def save(
        self,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ) -> None:
        if not self.description:
            self.description = self.default_description

        return super().save(force_insert, force_update, using, update_fields)

    @property
    def default_description(self):
        return settings.PROJECT_NAME


class OrderChargePaymentMethodCard(models.Model):
    payment_method = models.OneToOneField(
        OrderChargePaymentMethod,
        on_delete=models.CASCADE,
        related_name="card",
    )

    card_token = models.CharField(
        _("Card token"),
        max_length=512,
        null=True,
        blank=True,
    )
    brand = models.CharField(_("Card brand"), max_length=64, null=True)
    first_digits = models.CharField(
        _("First digits"),
        max_length=6,
        null=True,
        blank=True,
    )
    last_digits = models.CharField(
        _("Last digits"),
        max_length=4,
        null=True,
        blank=True,
    )
    exp_month = models.CharField(
        _("Expiration month"),
        max_length=2,
        null=True,
        blank=True,
    )
    exp_year = models.CharField(
        _("Expiration year"),
        max_length=4,
        null=True,
        blank=True,
    )
    holder_name = models.CharField(
        _("Holder name"),
        max_length=255,
        null=True,
        blank=True,
    )
    holder_document = models.CharField(
        _("Holder document"),
        max_length=64,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Order charge payment method card")
        verbose_name_plural = _("Order charge payment method cards")

    def __str__(self) -> str:
        return f"Card for {self.payment_method}"


class OrderQRCode(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="qr_codes")
    external_id = models.CharField(
        _("External id"),
        max_length=255,
        null=True,
        blank=True,
    )
    amount = models.PositiveIntegerField(_("Amount"))
    expiration = models.DateTimeField(
        _("Expiration"),
        default=get_default_qr_code_expiration,
    )
    text = models.TextField(_("Text"), null=True)
    png_link = models.URLField(_("PNG"), null=True)
    base64_link = models.URLField(_("Base64"), null=True)

    class Meta:
        verbose_name = _("Order QR Code")
        verbose_name_plural = _("Order QR Codes")

    def __str__(self) -> str:
        return f"QR Code for {self.order}"


class OrderChargePaymentMethodPIX(models.Model):
    payment_method = models.OneToOneField(
        OrderChargePaymentMethod,
        on_delete=models.CASCADE,
        related_name="pix",
    )

    holder_name = models.CharField(
        _("Holder name"),
        max_length=255,
        null=True,
        blank=True,
    )
    holder_document = models.CharField(
        _("Holder document"),
        max_length=64,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Order Charge Payment Method Pix")
        verbose_name_plural = _("Order Charge Payment Method Pix")

    def __str__(self) -> str:
        return f"PIX info for {self.payment_method.charge}"


class OrderSplit(models.Model):
    order = models.ForeignKey(
        Order,
        verbose_name=_("Order"),
        on_delete=models.CASCADE,
        related_name="splits",
    )
    account_external_id = models.CharField(_("Account external id"), max_length=255)
    is_platform = models.BooleanField(_("Is platform"), default=False)
    percentage = models.PositiveSmallIntegerField(_("Percentage"))

    objects = OrderSplitManager()

    class Meta:
        verbose_name = _("Order Charge Split")
        verbose_name_plural = _("Order Charge Splits")

    def __str__(self):
        return f"{self.account_external_id} - {self.percentage}% of {self.order}"
