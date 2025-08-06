from urllib.parse import urlencode

from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from django.utils.crypto import get_random_string

from companies.models import Company
from payments.integrations.pagbank.cache import (
    PAGBANK_OAUTH_AUTHORIZATION_COMPANY_CACHE_KEY,
)
from payments.integrations.pagbank.constants import (
    PAGBANK_APP_AUTHORIZATION_PERMISSIONS_FOR_SPLIT,
)


def get_app_authorization_redirection_url() -> str:
    api_url = settings.API_URL
    path = reverse("payments:integrations:pagbank:confirm-authorization")

    return f"{api_url}{path}"


def get_app_authorization_request_url(company: Company) -> str:
    url = settings.PAGBANK_CONNECT_BASE_URL + "/oauth2/authorize"
    client_id = settings.PAGBANK_APP_CLIENT_ID

    scope = " ".join(PAGBANK_APP_AUTHORIZATION_PERMISSIONS_FOR_SPLIT)

    state = get_random_string(64)

    company_request_key = PAGBANK_OAUTH_AUTHORIZATION_COMPANY_CACHE_KEY % state
    cache.set(company_request_key, company.pk, 600)

    params = {
        "response_type": "code",
        "client_id": client_id,
        "scope": scope,
        "state": state,
        "redirect_uri": get_app_authorization_redirection_url(),
    }

    return f"{url}?{urlencode(params)}"
