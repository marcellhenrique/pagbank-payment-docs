from django.urls import include, path

from payments.integrations.pagbank.views import (
    DisconnectPagBankAccountView,
    PagBankAuthorizationRedirectionView,
    PagBankPublicKeysView,
    RequestPagBankAuthorizationView,
)

app_name = "pagbank"


urlpatterns = [
    path("public-keys/", PagBankPublicKeysView.as_view(), name="public-keys"),
    path(
        "webhooks/",
        include(
            "payments.integrations.pagbank.webhooks.urls",
            namespace="pagbank_webhooks",
        ),
    ),
    path(
        "request-authorization/",
        RequestPagBankAuthorizationView.as_view(),
        name="request-authorization",
    ),
    path(
        "confirm-authorization/",
        PagBankAuthorizationRedirectionView.as_view(),
        name="confirm-authorization",
    ),
    path(
        "disconnect-account/",
        DisconnectPagBankAccountView.as_view(),
        name="disconnect-account",
    ),
]
