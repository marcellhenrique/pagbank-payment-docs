from typing import Unpack
from uuid import UUID

import requests
from celery.exceptions import MaxRetriesExceededError
from constance import config
from dateutil.relativedelta import relativedelta as rdelta
from django.utils import timezone
from rest_framework import status

from companies.models import Company
from core.helpers import exponential_backoff
from payments.factories import PaymentGatewayClientFactory
from payments.logs.models import RequestLog
from payments.mails import mail_payment_status_update
from payments.orders.models import OrderCharge
from payments.typing import MailUpdatePaymentStatusDTO
from trips.models import TripContractCharge
from wine_tour.celery import app, logger

MAX_RETRIES_QTY = 5


@app.task(bind=True, max_retries=MAX_RETRIES_QTY)
def create_order_and_charges_in_payment_gateway(
    self,
    charge_pk: UUID,
    gateway_name: str,
):
    try:
        payment_gateway_client = PaymentGatewayClientFactory(gateway_name).get_client()

        charge = OrderCharge.objects.get(pk=charge_pk)

        if charge.status != OrderCharge.Status.PROCESSING:
            charge.status = OrderCharge.Status.PROCESSING
            charge.save(update_fields=["status"])

        payment_gateway_client.create_credit_card_order(charge.order)
    except requests.HTTPError as error:
        if status.is_server_error(error.response.status_code):
            raise self.retry(
                countdown=exponential_backoff(self.request.retries),
            ) from error

        charge.status = OrderCharge.Status.FAILED
        charge.save(update_fields=["status"])

    except MaxRetriesExceededError:
        charge.status = OrderCharge.Status.FAILED
        charge.save(update_fields=["status"])

    except Exception as error:
        raise self.retry(
            countdown=exponential_backoff(self.request.retries),
        ) from error

    trip_contract_charge: TripContractCharge = (
        charge.to_trip_contract_charge.first().trip_contract_charge
    )
    company = trip_contract_charge.company

    send_email_with_payment_status_update.delay(
        company_pk=company.pk,
        language="pt_BR",
        charge_pk=charge.pk,
        email=charge.order.customer.email,
    )


@app.task
def send_email_with_payment_status_update(
    **kwargs: Unpack[MailUpdatePaymentStatusDTO],
):
    mail_payment_status_update(**kwargs)


@app.task(bind=True, max_retries=MAX_RETRIES_QTY)
def cancel_payment(self, charge_id: int, company_id: int):
    charge = OrderCharge.objects.filter(reference_id=charge_id).first()

    if not charge:
        return

    company = Company.objects.get(id=company_id)

    payment_gateway = PaymentGatewayClientFactory(
        charge.order.payment_gateway,
    ).get_client()

    charge.cancel_status = OrderCharge.CancelStatus.PROCESSING
    charge.save(update_fields=["cancel_status"])

    payment_gateway.cancel_payment(charge, company)


@app.task
def delete_old_payment_requests_logs():
    retention_period = config.PAYMENT_REQUESTS_LOGS_RETENTION_PERIOD
    cut_date = timezone.now() - rdelta(days=retention_period)

    queryset = RequestLog.objects.filter(
        timestamp__lte=cut_date,
    )
    logger.info(
        f"Deleting payment-related requests logs created before {cut_date} ({queryset.count()})",
    )

    if queryset.exists():
        queryset.delete()
