import hashlib
import json

from django.conf import settings
from django.urls import reverse


def generate_signature(token: str, request_body: dict) -> str:
    # https://developer.pagbank.com.br/reference/confirmar-autenticidade-da-notificacao
    unformatted_json_str = json.dumps(request_body, separators=(",", ":"))

    combined_string = token + "-" + unformatted_json_str

    return hashlib.sha256(combined_string.encode()).hexdigest()


def get_orders_webhook_url() -> str:
    api_url = settings.API_URL
    path = reverse("payments:integrations:pagbank:pagbank_webhooks:orders")

    return f"{api_url}{path}"
