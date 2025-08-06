from django.db import transaction
from rest_framework import serializers

from payments.orders.models import (
    Order,
    OrderCharge,
    OrderChargePaymentMethod,
    OrderChargePaymentMethodPIX,
)
from trips.models import TripContractChargePaymentRelation


class PagBankPixHolderSerializer(serializers.Serializer):
    class Meta:
        fields = [
            "name",
            "tax_id",
        ]


class PagBankPixSerializer(serializers.ModelSerializer):
    holder = PagBankPixHolderSerializer(write_only=True, required=False)

    class Meta:
        model = OrderChargePaymentMethodPIX
        fields = [
            "id",
            "payment_method",
            "holder",
            "holder_name",
            "holder_document",
        ]
        extra_kwargs = {
            "payment_method": {
                "required": False,
            },
            "holder_name": {
                "required": False,
            },
            "holder_document": {
                "required": False,
            },
        }

    def to_internal_value(self, data):
        if holder := data.pop("holder", None):
            data["holder_name"] = holder.get("name")
            data["holder_document"] = holder.get("document")

        return super().to_internal_value(data)


class PagBankPaymentMethodSerializer(serializers.ModelSerializer):
    pix = PagBankPixSerializer()
    charge = serializers.PrimaryKeyRelatedField(
        queryset=OrderCharge.objects.all(),
        required=False,
    )

    class Meta:
        model = OrderChargePaymentMethod
        fields = [
            "charge",
            "type",
            "pix",
        ]

    def create(self, validated_data):
        pix_data = validated_data.pop("pix")

        instance = super().create(validated_data)

        pix_data["payment_method"] = instance
        pix = PagBankPixSerializer(data=pix_data)
        pix.create(pix_data)

        return instance


class PagBankChargeWebhookSerializer(serializers.ModelSerializer):
    payment_method = PagBankPaymentMethodSerializer()
    amount = serializers.SerializerMethodField()

    class Meta:
        model = OrderCharge
        fields = [
            "id",
            "order",
            "status",
            "paid_at",
            "amount",
            "value",
            "currency",
            "payment_method",
        ]
        extra_kwargs = {
            "id": {
                "source": "external_id",
            },
            "order": {
                "required": False,
            },
            "amount": {
                "write_only": True,
            },
        }

    def to_internal_value(self, data: dict):
        amount = data.get("amount")
        data["value"] = amount.get("value")
        data["currency"] = amount.get("currency")

        return super().to_internal_value(data)

    @transaction.atomic
    def create(self, validated_data):
        payment_method_data = validated_data.pop("payment_method")

        instance: OrderCharge = super().create(validated_data)

        payment_method_data["charge"] = instance
        payment_method = PagBankPaymentMethodSerializer(data=payment_method_data)
        payment_method = payment_method.create(payment_method_data)

        if payment_method.type == OrderChargePaymentMethod.Types.PIX and (
            qr_code := instance.order.qr_codes.first()
        ):
            charge_relation: TripContractChargePaymentRelation = (
                qr_code.to_trip_contract_charge.first()
            )
            charge_relation.payment_charge = instance
            charge_relation.save(update_fields=["payment_charge"])

        return instance


class PagBankOrderWebhookSerializer(serializers.ModelSerializer):
    charges = PagBankChargeWebhookSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            "reference_id",
            "charges",
        ]

    def update(self, instance, validated_data):
        charges_data = validated_data.pop("charges")

        for i in range(len(charges_data)):
            charges_data[i]["order"] = instance

        PagBankChargeWebhookSerializer(data=charges_data, many=True).create(
            charges_data,
        )

        return super().update(instance, validated_data)
