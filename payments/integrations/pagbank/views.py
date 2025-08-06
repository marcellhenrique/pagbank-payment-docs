from b2_utils.permissions import IsValidVersion
from django.core.cache import cache
from django.shortcuts import redirect
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.permissions.classes import IsCompanyUser
from companies.models import Company, CompanyPaymentInfo
from companies.permissions import CanRequestPaymentGatewayAuthorization
from payments.exceptions import PaymentGatewayClientRequestFailedError
from payments.integrations.pagbank.cache import (
    PAGBANK_OAUTH_AUTHORIZATION_COMPANY_CACHE_KEY,
)
from payments.integrations.pagbank.client import PagBankClient
from payments.integrations.pagbank.constants import (
    FRONTEND_APP_OAUTH_REDIRECT_FAIL_URL,
    FRONTEND_APP_OAUTH_REDIRECT_SUCCESS_URL,
)
from payments.integrations.pagbank.helpers import get_app_authorization_request_url
from payments.integrations.pagbank.serializers import PagBankPublicKeySerializer
from payments.integrations.pagbank.tasks import get_client_info


class PagBankPublicKeysView(GenericAPIView):
    serializer_class = PagBankPublicKeySerializer

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        responses={status.HTTP_200_OK: PagBankPublicKeySerializer},
    )
    def get(self, request: Request) -> Response:
        pagbank_client = PagBankClient()

        try:
            public_key = pagbank_client.get_public_key()
        except PaymentGatewayClientRequestFailedError:
            return Response(
                {"An error has ocurred"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"key": public_key},
            status=status.HTTP_200_OK,
        )


class RequestPagBankAuthorizationView(APIView):
    permission_classes = [
        IsValidVersion,
        IsCompanyUser,
        CanRequestPaymentGatewayAuthorization,
    ]

    def post(self, request: Request) -> Response:
        company = request.user.company
        url = get_app_authorization_request_url(company)

        return Response({"authorization_url": url}, status=status.HTTP_200_OK)


class PagBankAuthorizationRedirectionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        # TODO: save this code somewhere and call the async task
        #       to get the account_id
        code = request.query_params.get("code")  # noqa
        state = request.query_params.get("state")
        cache_key = PAGBANK_OAUTH_AUTHORIZATION_COMPANY_CACHE_KEY % state

        company_id = cache.get(cache_key)

        if not company_id:
            return redirect(FRONTEND_APP_OAUTH_REDIRECT_FAIL_URL)

        get_client_info.delay(company_id, code)

        return redirect(FRONTEND_APP_OAUTH_REDIRECT_SUCCESS_URL)


class DisconnectPagBankAccountView(APIView):
    permission_classes = [
        IsValidVersion,
        IsCompanyUser,
        CanRequestPaymentGatewayAuthorization,
    ]

    def post(self, request: Request) -> Response:
        company: Company = request.user.company
        payment_info: CompanyPaymentInfo = company.payment_info

        payment_info.payment_account_authorization_status = (
            CompanyPaymentInfo.PaymentAccountAuthorizationStatus.PENDING
        )
        payment_info.payment_account_id = None
        payment_info.save(
            update_fields=[
                "payment_account_authorization_status",
                "payment_account_id",
            ],
        )

        return Response(status=status.HTTP_204_NO_CONTENT)
