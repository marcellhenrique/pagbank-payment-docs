from contextlib import suppress

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response as DRFResponse
from sentry_sdk import capture_exception

from companies.models import Company
from payments.base import BasePaymentGatewayClient
from payments.exceptions import PaymentGatewayClientRequestFailedError
from payments.integrations.pagbank.enums import ChargePaymentStatus
from payments.integrations.pagbank.models import PagBankPublicKey
from payments.integrations.pagbank.serializers import (
    PagBankCancelChargeSerializer,
    PagBankOrderCreditCardPaymentResponseSerializer,
    PagBankOrderSerializer,
    PagBankPixOrderResponseSerializer,
    PagBankPixOrderSerializer,
)
from payments.integrations.pagbank.typing import PagBankPublicKeyResponse
from payments.integrations.pagbank.webhooks.serializers import (
    PagBankOrderWebhookSerializer,
)
from payments.logs.helpers import log_from_request, log_from_requests_response
from payments.orders.models import Order, OrderCharge
from trips.models import TripContractCharge, TripContractChargePaymentRelation

PAYMENT_STATUS_MAPPING = {
    ChargePaymentStatus.IN_ANALYSIS: OrderCharge.Status.PROCESSING,
    ChargePaymentStatus.CANCELED: OrderCharge.Status.CANCELED,
    ChargePaymentStatus.DECLINED: OrderCharge.Status.DECLINED,
    ChargePaymentStatus.AUTHORIZED: OrderCharge.Status.AUTHORIZED,
    ChargePaymentStatus.PAID: OrderCharge.Status.PAID,
    ChargePaymentStatus.WAITING: OrderCharge.Status.PENDING,
}

TRIP_CHARGE_STATUS_MAPPING = {
    OrderCharge.Status.AUTHORIZED: TripContractCharge.Status.PENDING,
    OrderCharge.Status.CANCELED: TripContractCharge.Status.REFUNDED,
    OrderCharge.Status.CREATED: TripContractCharge.Status.PENDING,
    OrderCharge.Status.DECLINED: TripContractCharge.Status.PENDING,
    OrderCharge.Status.PAID: TripContractCharge.Status.PAID,
    OrderCharge.Status.FAILED: TripContractCharge.Status.PENDING,
    OrderCharge.Status.PROCESSING: TripContractCharge.Status.PENDING,
}


class PagBankClient(BasePaymentGatewayClient):
    """
    Client to interact with the PagBank API, handling public key creation and management.
    """

    MAX_RETRIES = 5
    PUBLIC_KEYS_ENDPOINT = "/public-keys"
    CHANGE_PUBLIC_KEY_ENDPOINT = "/public-keys/card"
    ORDER_ENDPOINT = "/orders"
    CANCEL_CHARGES_ENDPOINT = "/charges/{charge_id}/cancel"

    def __init__(self) -> None:
        self.api_url = self.get_api_url()
        self.api_token = self.get_api_token()
        self.request_timeout = 30  # Set a default timeout or retrieve it from settings

    @classmethod
    def get_api_token(cls) -> str:
        return settings.PAGBANK_API_TOKEN

    @classmethod
    def get_api_url(cls) -> str:
        return settings.PAGBANK_API_URL

    @classmethod
    def get_webhook_key(cls) -> str:
        return settings.PAGBANK_WEBHOOK_API_KEYS

    def _get_headers(self) -> dict:
        """Construct the headers for the API requests."""
        return {
            "accept": "*/*",
            "Authorization": f"Bearer {self.api_token}",
            "content-type": "application/json",
        }

    def create_public_key(self) -> requests.Response:
        try:
            url = f"{self.api_url}{self.PUBLIC_KEYS_ENDPOINT}"
            headers = self._get_headers()
            payload = {"type": "card"}

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.request_timeout,
            )

            log_from_requests_response(
                response,
                redacted_fields={"request_headers": [{"key": "Authorization"}]},
            )

            response.raise_for_status()  # Raise an HTTPError for bad responses
            return response

        except requests.exceptions.RequestException as error:
            capture_exception(error)
            error_msg = "Failed to create a public key"

            raise PaymentGatewayClientRequestFailedError(
                error_msg,
            ) from error

    def change_public_key(self) -> requests.Response:
        try:
            url = f"{self.api_url}{self.CHANGE_PUBLIC_KEY_ENDPOINT}"
            headers = self._get_headers()

            response = requests.put(
                url,
                headers=headers,
                timeout=self.request_timeout,
            )

            log_from_requests_response(
                response,
                redacted_fields={"request_headers": [{"key": "Authorization"}]},
            )

            response.raise_for_status()  # Raise an HTTPError for bad responses
            return response

        except requests.exceptions.RequestException as error:
            capture_exception(error)
            error_msg = "Failed to change the public key"

            raise PaymentGatewayClientRequestFailedError(
                error_msg,
            ) from error

    def get_existing_public_key_from_db(self) -> PagBankPublicKey:
        return PagBankPublicKey.valid_objects.order_by("-created_at").first()

    def get_public_key(self) -> str:
        """
        Retrieve the public key, either from the database or by creating a new one.

        If a valid key exists in the database, it is returned. Otherwise, a new key is created.
        If the newly created key already exists but is expired, a request is made to change the key.
        The key is then stored in the database.

        Returns:
            str: The public key.

        Raises:
            PaymentGatewayClientRequestFailedError: If requests to create or change the key fail.
        """
        if existing_key := self.get_existing_public_key_from_db():
            return existing_key.key

        create_response = self.create_public_key()
        response_data: PagBankPublicKeyResponse = create_response.json()

        if PagBankPublicKey.objects.filter(
            key=response_data["public_key"],
            expired=True,
        ).exists():
            change_response = self.change_public_key()
            response_data = change_response.json()

        instance: PagBankPublicKey = (
            PagBankPublicKey.valid_objects.create_from_api_response_data(
                **response_data,
            )
        )

        return instance.key

    def create_credit_card_order(self, order: Order) -> requests.Response:
        url = f"{self.api_url}{self.ORDER_ENDPOINT}"
        headers = self._get_headers()

        serializer = PagBankOrderSerializer(order)
        data = serializer.data

        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=self.request_timeout,
        )

        log_from_requests_response(
            response,
            redacted_fields={"request_headers": [{"key": "Authorization"}]},
        )
        response.raise_for_status()

        response_serializer = PagBankOrderCreditCardPaymentResponseSerializer(
            order,
            data=response.json(),
        )
        response_serializer.is_valid(raise_exception=True)
        response_serializer.save()

        charge: OrderCharge = order.charges.first()
        trip_contract_charge: TripContractCharge = (
            charge.to_trip_contract_charge.first().trip_contract_charge
        )

        trip_contract_charge.status = TripContractCharge.Status.PAID
        trip_contract_charge.paid_at = charge.paid_at
        trip_contract_charge.save()

        return response

    def create_pix_order(self, order: Order) -> requests.Response:
        url = f"{self.api_url}{self.ORDER_ENDPOINT}"
        headers = self._get_headers()

        serializer = PagBankPixOrderSerializer(order)
        data = serializer.data

        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=self.request_timeout,
        )

        log_from_requests_response(
            response,
            redacted_fields={"request_headers": [{"key": "Authorization"}]},
        )
        response.raise_for_status()

        serializer = PagBankPixOrderResponseSerializer(order, data=response.json())
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return response

    def update_pix_order(
        self,
        request: Request,
        order: Order,
        data: dict,
    ) -> DRFResponse:
        from payments.tasks import send_email_with_payment_status_update

        serializer = PagBankOrderWebhookSerializer(order, data=data)

        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as err:
            response = DRFResponse(
                err.detail,
                status=status.HTTP_400_BAD_REQUEST,
            )

            log_from_request(
                request,
                response,
            )

            return response

        serializer.save()

        order.refresh_from_db()

        charge: OrderCharge = order.charges.first()

        if not charge:
            return None

        with suppress(AttributeError), transaction.atomic():
            charge_relation: TripContractChargePaymentRelation = (
                order.qr_codes.first().to_trip_contract_charge.first()
            )
            charge_relation.payment_charge = charge
            charge_relation.save()
            trip_contract_charge: TripContractCharge = (
                charge_relation.trip_contract_charge
            )
            trip_contract_charge.status = TRIP_CHARGE_STATUS_MAPPING[charge.status]
            trip_contract_charge.paid_at = charge.paid_at
            trip_contract_charge.save()

            company = trip_contract_charge.order.contract.trip.deal.company

            send_email_with_payment_status_update.delay(
                company_pk=company.pk,
                language="pt_BR",
                charge_pk=charge.pk,
                email=charge.order.customer.email,
            )

        response = DRFResponse(status=status.HTTP_204_NO_CONTENT)

        log_from_request(
            request,
            response,
        )

        return response

    def cancel_payment(self, charge: OrderCharge, company: Company):
        from payments.tasks import send_email_with_payment_status_update

        path = self.CANCEL_CHARGES_ENDPOINT.format(charge_id=charge.external_id)
        url = f"{self.api_url}{path}"
        headers = self._get_headers()

        serializer = PagBankCancelChargeSerializer(charge)
        data = serializer.data

        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=self.request_timeout,
        )

        log_from_requests_response(
            response,
            redacted_fields={"request_headers": [{"key": "Authorization"}]},
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            charge.cancel_status = OrderCharge.CancelStatus.FAILED
            charge.save(update_fields=["cancel_status"])

            capture_exception(error)

            return None

        charge.status = OrderCharge.Status.CANCELED
        charge.cancel_status = OrderCharge.CancelStatus.CANCELED
        charge.canceled_at = timezone.now()
        charge.save(update_fields=["status", "cancel_status", "canceled_at"])

        trip_contract_charge: TripContractCharge = (
            charge.to_trip_contract_charge.first().trip_contract_charge
        )

        trip_contract_charge.status = TripContractCharge.Status.REFUNDED
        trip_contract_charge.paid_at = charge.paid_at
        trip_contract_charge.save()

        send_email_with_payment_status_update.delay(
            charge_pk=charge.pk,
            company_pk=company.pk,
            language="pt_BR",
            email=charge.order.customer.email,
        )

        return response
