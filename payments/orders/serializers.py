from b2_utils.validators import validate_cnpj, validate_cpf
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from core.fields import DynamicFieldsSerializer
from payments.orders.models import (
    Address,
    Customer,
    Order,
    OrderCharge,
    OrderChargePaymentMethod,
    OrderChargePaymentMethodCard,
    OrderChargePaymentMethodPIX,
    OrderQRCode,
    Phone,
)

CPF_CHAR_LENGTH = 11
CNPJ_CHAR_LENGTH = 14


class CustomerPhoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Phone
        fields = [
            "customer",
            "country_code",
            "area_code",
            "number",
        ]

        extra_kwargs = {
            "customer": {
                "required": False,
            },
        }


class CustomerAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "id",
            "street",
            "number",
            "district",
            "city",
            "state",
            "additional_info",
        ]


class CustomerSerializer(serializers.ModelSerializer):
    phone = CustomerPhoneSerializer()
    address = CustomerAddressSerializer()

    class Meta:
        model = Customer
        fields = [
            "name",
            "email",
            "document",
            "phone",
            "address",
        ]

    def validate_document(self, document: str) -> str:
        if len(document) == CNPJ_CHAR_LENGTH:
            validate_cnpj(document)

        elif len(document) == CPF_CHAR_LENGTH:
            validate_cpf(document)

        else:
            raise ValidationError(
                _("Invalid document number. Must be a CPF or CNPJ."),
                code="invalid_document_number",
            )

        return document

    @transaction.atomic
    def create(self, validated_data: dict):
        phone_data = validated_data.pop("phone")
        address_data = validated_data.pop("address")

        address_serializer = CustomerAddressSerializer(data=address_data)
        address_serializer.is_valid(raise_exception=True)
        validated_data["address"] = address_serializer.save()

        customer: Customer = super().create(validated_data)
        phone_data["customer"] = customer.pk

        phone_serializer = CustomerPhoneSerializer(data=phone_data)
        phone_serializer.is_valid(raise_exception=True)
        phone_serializer.save()

        return customer


class OrderSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer()

    class Meta:
        model = Order
        fields = ["customer", "payment_gateway"]
        extra_kwargs = {
            "payment_gateway": {"required": False},
        }

    @transaction.atomic
    def create(self, validated_data: dict):
        customer_data = validated_data.pop("customer")

        customer_serializer = CustomerSerializer(data=customer_data)
        customer_serializer.is_valid(raise_exception=True)

        validated_data["customer"] = customer_serializer.save()

        return super().create(validated_data)


class OrderQRCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderQRCode
        fields = [
            "amount",
            "text",
            "png_link",
            "base64_link",
            "expiration",
        ]


class OrderChargePaymentMethodCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderChargePaymentMethodCard
        fields = [
            "brand",
            "first_digits",
            "last_digits",
            "exp_month",
            "exp_year",
            "holder_name",
            "holder_document",
        ]


class OrderChargePaymentMethodPIXSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderChargePaymentMethodPIX
        fields = [
            "holder_name",
            "holder_document",
        ]


class OrderChargePaymentMethodSerializer(serializers.ModelSerializer):
    card = serializers.SerializerMethodField()
    pix = serializers.SerializerMethodField()

    class Meta:
        model = OrderChargePaymentMethod
        fields = [
            "type",
            "installments",
            "operation_type",
            "description",
            "card",
            "pix",
        ]

    def get_card(self, obj: OrderChargePaymentMethod) -> dict:
        if not (card := getattr(obj, "card", None)):
            return None

        return OrderChargePaymentMethodCardSerializer(card).data

    def get_pix(self, obj: OrderChargePaymentMethod) -> dict:
        if not (pix := getattr(obj, "pix", None)):
            return None

        return OrderChargePaymentMethodPIXSerializer(pix).data


class OrderChargeSerializer(DynamicFieldsSerializer, serializers.ModelSerializer):
    order = OrderSerializer()
    payment_method = OrderChargePaymentMethodSerializer()

    class Meta:
        model = OrderCharge
        fields = [
            "reference_id",
            "order",
            "payment_method",
            "description",
            "value",
            "currency",
            "status",
            "cancel_status",
            "paid_at",
        ]
