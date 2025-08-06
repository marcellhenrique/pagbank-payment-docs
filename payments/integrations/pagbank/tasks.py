import requests
from django.conf import settings
from rest_framework import status
from sentry_sdk import capture_exception

from companies.models import Company, CompanyPaymentInfo
from payments.integrations.pagbank.helpers import get_app_authorization_redirection_url
from payments.integrations.pagbank.serializers import (
    PagBankConnectAuthorizationSerializer,
)
from payments.logs.helpers import log_from_requests_response
from wine_tour.celery import app


@app.task
def get_client_info(company_id: int, code: str):
    company = Company.objects.get(id=company_id)
    payment_info: CompanyPaymentInfo = company.payment_info

    if (
        payment_info.payment_account_authorization_status
        != CompanyPaymentInfo.PaymentAccountAuthorizationStatus.PROCESSING
    ):
        payment_info.payment_account_authorization_status = (
            CompanyPaymentInfo.PaymentAccountAuthorizationStatus.PROCESSING
        )
        payment_info.save(update_fields=["payment_account_authorization_status"])

    url = settings.PAGBANK_API_URL + "/oauth2/token"

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": get_app_authorization_redirection_url(),
    }
    headers = {
        "X_CLIENT_ID": settings.PAGBANK_APP_CLIENT_ID,
        "X_CLIENT_SECRET": settings.PAGBANK_APP_CLIENT_SECRET,
        "Authorization": f"Bearer {settings.PAGBANK_API_TOKEN}",
    }

    response = requests.post(url, json=data, headers=headers, timeout=300)

    def authorization_failed():
        payment_info.payment_account_authorization_status = (
            CompanyPaymentInfo.PaymentAccountAuthorizationStatus.FAILED
        )
        payment_info.save(update_fields=["payment_account_authorization_status"])

    log_from_requests_response(
        response,
        redacted_fields={
            "request_headers": [{"key": "Authorization"}, {"key": "X_CLIENT_SECRET"}],
        },
    )

    if not status.is_success(response.status_code):
        authorization_failed()
        return

    serializer = PagBankConnectAuthorizationSerializer(data=response.json())

    try:
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
    except Exception as error:
        authorization_failed()
        capture_exception(error)
        return

    payment_info.payment_account_id = instance.account_id
    payment_info.payment_account_authorization_status = (
        CompanyPaymentInfo.PaymentAccountAuthorizationStatus.AUTHORIZED
    )
    payment_info.save(
        update_fields=["payment_account_id", "payment_account_authorization_status"],
    )
