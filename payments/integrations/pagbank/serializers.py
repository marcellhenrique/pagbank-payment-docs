from django.db import transaction
from rest_framework import serializers

from payments.integrations.pagbank.enums import QRCodeLinkTypes, SplitMethods
from payments.integrations.pagbank.models import PagBankConnectAuthorization
from payments.integrations.pagbank.webhooks.helpers import get_orders_webhook_url
from payments.orders.models import (
    Customer,
    Order,
    OrderCharge,
    OrderChargePaymentMethod,
    OrderChargePaymentMethodCard,
    OrderItem,
    OrderQRCode,
    OrderSplit,
    Phone,
)


class PagBankPublicKeySerializer(serializers.Serializer):
    key = serializers.CharField()


class PagBankOrderCustomerPhoneSerializer(serializers.ModelSerializer):
    country = serializers.CharField(source="country_code")
    area = serializers.CharField(source="area_code")
    type = serializers.SerializerMethodField()

    class Meta:
        model = Phone
        fields = [
            "country",
            "area",
            "number",
            "type",
        ]

    def get_type(self, _) -> str:
        return "MOBILE"


class PagBankOrderCustomerSerializer(serializers.ModelSerializer):
    tax_id = serializers.CharField(source="document")
    phones = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            "name",
            "email",
            "tax_id",
            "phones",
        ]

    def get_phones(self, obj: Customer) -> list[PagBankOrderCustomerPhoneSerializer]:
        return [
            PagBankOrderCustomerPhoneSerializer(obj.phone).data,
        ]


class PagBankOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "reference_id",
            "name",
            "quantity",
            "unit_amount",
        ]


class PagBankChargeCreditCardPaymentMethodSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    capture = serializers.SerializerMethodField()
    card = serializers.SerializerMethodField()

    class Meta:
        model = OrderChargePaymentMethod
        fields = [
            "type",
            "installments",
            "capture",
            "card",
        ]

    def get_type(self, _) -> str:
        return "CREDIT_CARD"

    def get_capture(self, _) -> bool:
        return True

    def get_card(self, obj: OrderChargePaymentMethod) -> dict:
        return {
            "encrypted": obj.card.card_token,
        }


class PagBankSplitReceiverSerializer(serializers.ModelSerializer):
    account = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()

    class Meta:
        model = OrderSplit
        fields = [
            "account",
            "amount",
        ]

    def get_account(self, obj: OrderSplit) -> dict:
        return {
            "id": obj.account_external_id,
        }

    def get_amount(self, obj: OrderSplit) -> dict:
        return {
            "value": obj.percentage,
        }


class PagBankChargeSerializer(serializers.ModelSerializer):
    amount = serializers.SerializerMethodField()
    payment_method = PagBankChargeCreditCardPaymentMethodSerializer()
    splits = serializers.SerializerMethodField()

    class Meta:
        model = OrderCharge
        fields = [
            "reference_id",
            "description",
            "amount",
            "payment_method",
            "splits",
        ]

    def get_amount(self, obj: OrderCharge) -> dict:
        return {
            "value": obj.value,
            "currency": "BRL",
        }

    def get_splits(self, obj: OrderCharge) -> dict:
        return {
            "method": SplitMethods.PERCENTAGE.value,
            "receivers": PagBankSplitReceiverSerializer(
                obj.order.splits.all(),
                many=True,
            ).data,
        }


class PagBankOrderSerializer(serializers.ModelSerializer):
    """
    Serializer used when SENDING information to PagBank
    """

    customer = PagBankOrderCustomerSerializer()
    items = PagBankOrderItemSerializer(many=True)
    charges = PagBankChargeSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            "reference_id",
            "customer",
            "items",
            "charges",
        ]


class PagBankCardDataCreditCardPaymentResponseSerializer(serializers.ModelSerializer):
    holder = serializers.SerializerMethodField()

    class Meta:
        model = OrderChargePaymentMethodCard
        fields = [
            "card_token",
            "brand",
            "first_digits",
            "last_digits",
            "exp_month",
            "exp_year",
            "holder_name",
            "holder_document",
            "holder",
        ]
        extra_kwargs = {
            "payment_method": {"write_only": True},
        }

    def save(self, **kwargs):
        holder_data = self.initial_data.pop("holder", None)

        if holder_data:
            self.instance.holder_name = holder_data.get("name")
            self.instance.holder_document = holder_data.get("document")

        for attr, value in self.validated_data.items():
            setattr(self.instance, attr, value)

        self.instance.save()


class PagBankPaymentMethodCreditCardPaymentResponseSerializer(serializers.Serializer):
    card = PagBankCardDataCreditCardPaymentResponseSerializer()

    class Meta:
        fields = [
            "card",
        ]


class PagBankChargeCreditCardPaymentResponseSerializer(serializers.Serializer):
    class Meta:
        fields = [
            "id",
            "reference_id",
            "status",
            "paid_at",
            "payment_method",
        ]


class PagBankOrderCreditCardPaymentResponseSerializer(serializers.ModelSerializer):
    """
    Serializer used when RECEIVING information from PagBank
    (validate the responses' payload)
    """

    charges = PagBankChargeCreditCardPaymentResponseSerializer(many=True)
    id = serializers.CharField(source="external_id")

    class Meta:
        model = Order
        fields = [
            "id",
            "reference_id",
            "charges",
        ]

    def validate(self, attrs):
        attrs["charges"] = self.initial_data["charges"]

        return super().validate(attrs)

    @transaction.atomic
    def save(self, **kwargs):
        self.instance.external_id = self.validated_data["external_id"]
        self.instance.save()

        charge_data: dict = self.validated_data["charges"][0]
        charge: OrderCharge = self.instance.charges.first()

        charge.external_id = charge_data["id"]
        charge.status = charge_data["status"]

        if paid_at := charge_data.pop("paid_at"):
            charge.paid_at = paid_at

        charge.save()

        payment_method_data = charge_data["payment_method"]
        card_data = payment_method_data["card"]

        card = PagBankCardDataCreditCardPaymentResponseSerializer(
            charge.payment_method.card,
            data=card_data,
        )
        card.is_valid(raise_exception=True)
        card.save()

        return self.instance


class PagBankQRCodeSerializer(serializers.ModelSerializer):
    amount = serializers.SerializerMethodField()
    expiration_date = serializers.DateTimeField(source="expiration")
    splits = serializers.SerializerMethodField()

    class Meta:
        model = OrderQRCode
        fields = [
            "amount",
            "expiration_date",
            "splits",
        ]

    def get_amount(self, obj: OrderQRCode) -> dict:
        return {
            "value": obj.amount,
        }

    def get_splits(self, obj: OrderQRCode) -> dict:
        return {
            "method": SplitMethods.PERCENTAGE.value,
            "receivers": PagBankSplitReceiverSerializer(
                obj.order.splits.all(),
                many=True,
            ).data,
        }


class PagBankPixOrderSerializer(serializers.ModelSerializer):
    """
    Serializer used when SENDING information to PagBank
    """

    customer = PagBankOrderCustomerSerializer()
    items = PagBankOrderItemSerializer(many=True)
    notification_urls = serializers.SerializerMethodField()
    qr_codes = PagBankQRCodeSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            "reference_id",
            "customer",
            "items",
            "qr_codes",
            "notification_urls",
        ]

    def get_notification_urls(self, _) -> list[str]:
        return [get_orders_webhook_url()]


class PagBankPixQRCodeResponseSerializer(serializers.Serializer):
    class Meta:
        fields = [
            "id",
            "expiration_date",
            "amount",
            "text",
        ]


class PagBankPixOrderResponseSerializer(serializers.ModelSerializer):
    qr_codes = PagBankPixQRCodeResponseSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "reference_id",
            "qr_codes",
        ]
        extra_kwargs = {
            "id": {
                "source": "external_id",
            },
        }

    def validate(self, attrs):
        attrs["qr_codes"] = self.initial_data["qr_codes"]

        return super().validate(attrs)

    @transaction.atomic
    def save(self, **kwargs):
        self.instance.external_id = self.validated_data.get("external_id")
        self.instance.save()

        qr_codes = self.validated_data.get("qr_codes", [])
        qr_code: OrderQRCode = self.instance.qr_codes.first()

        links = {link["rel"]: link for link in qr_codes[0]["links"]}

        qr_code.external_id = qr_codes[0]["id"]
        qr_code.text = qr_codes[0]["text"]
        qr_code.png_link = links[QRCodeLinkTypes.PNG.value]["href"]
        qr_code.base64_link = links[QRCodeLinkTypes.BASE64.value]["href"]

        qr_code.save()

        return self.instance


class PagBankConnectAuthorizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PagBankConnectAuthorization
        fields = [
            "id",
            "scope",
            "account_id",
        ]


class PagBankCancelChargeSplitReceiverConfigurationSerializer(
    serializers.ModelSerializer,
):
    refund = serializers.SerializerMethodField()

    class Meta:
        model = OrderSplit
        fields = [
            "refund",
        ]

    def get_refund(self, obj: OrderSplit) -> dict:
        refund_data = {
            "rounding_liable": {"apply": obj.is_platform},
        }

        if obj.is_platform:
            refund_data["fee_liable"] = {
                "percentage": 100,
            }

        return refund_data


class PagBankCancelChargeSplitReceiversSerializer(serializers.ModelSerializer):
    account = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    configurations = serializers.SerializerMethodField()

    class Meta:
        model = OrderSplit
        fields = [
            "account",
            "amount",
            "configurations",
        ]

    def get_account(self, obj: OrderSplit) -> dict:
        return {
            "id": obj.account_external_id,
        }

    def get_amount(self, obj: OrderSplit) -> dict:
        return {
            "value": obj.percentage,
        }

    def get_configurations(self, obj: OrderSplit) -> dict:
        return PagBankCancelChargeSplitReceiverConfigurationSerializer(
            obj,
        ).data


class PagBankCancelChargesSplitSerializer(serializers.ModelSerializer):
    method = serializers.SerializerMethodField()
    receivers = serializers.SerializerMethodField()

    class Meta:
        model = OrderCharge
        fields = [
            "method",
            "receivers",
        ]

    def get_method(self, _) -> dict:
        return "PERCENTAGE"

    def get_receivers(self, obj: OrderCharge) -> dict:
        return PagBankCancelChargeSplitReceiversSerializer(
            obj.order.splits.all(),
            many=True,
        ).data


class PagBankCancelChargeSerializer(serializers.ModelSerializer):
    splits = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()

    class Meta:
        model = OrderCharge
        fields = [
            "amount",
            "splits",
        ]

    def get_splits(self, obj: OrderCharge) -> dict:
        return PagBankCancelChargesSplitSerializer(obj).data

    def get_amount(self, obj: OrderCharge) -> dict:
        return {
            "value": obj.value,
        }
