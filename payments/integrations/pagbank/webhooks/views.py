from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from payments.integrations.pagbank.client import PagBankClient
from payments.integrations.pagbank.webhooks.authentication_classes import (
    PagBankTokenAuthentication,
)
from payments.integrations.pagbank.webhooks.serializers import (
    PagBankOrderWebhookSerializer,
)
from payments.orders.models import Order
from wine_tour.settings.enums import SystemEnvironments


class PagBankOrderWebHook(GenericAPIView):
    serializer_class = PagBankOrderWebhookSerializer

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        # Currently, this webhook is exclusively used for Pix-related orders,
        # which is why the update_pix_order method is invoked.

        # However, this may change in the future, so be aware that new types of
        # order updates might be introduced, and this code will need to be adjusted.

        order_id = request.headers.get("x-product-id")
        order = get_object_or_404(Order, external_id=order_id)

        return PagBankClient().update_pix_order(request, order, request.data)

    @property
    def authentication_classes(self):
        if settings.ENVIRONMENT != SystemEnvironments.PRODUCTION:
            return []

        return [PagBankTokenAuthentication]
