import json

from django.contrib.auth.models import AnonymousUser
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from payments.integrations.pagbank.client import PagBankClient
from payments.integrations.pagbank.webhooks.helpers import generate_signature


class PagBankTokenAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request: Request):
        # https://developer.pagbank.com.br/reference/confirmar-autenticidade-da-notificacao

        token = request.headers.get("X-Authenticity-Token")
        expected_token = generate_signature(
            PagBankClient().get_api_token(),
            json.dumps(request.data, separators=(",", ":")),
        )

        if not token or (token != expected_token):
            raise AuthenticationFailed

        return (AnonymousUser, None)
