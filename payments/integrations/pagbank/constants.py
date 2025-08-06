from django.conf import settings

PAGBANK_APP_AUTHORIZATION_PERMISSIONS_FOR_SPLIT = [
    "accounts.read",
    "payments.refund",
    "payments.split.read",
]

FRONTEND_APP_OAUTH_REDIRECT_SUCCESS_URL = (
    f"{settings.FRONT_END_URL}/integration/success"
)
FRONTEND_APP_OAUTH_REDIRECT_FAIL_URL = f"{settings.FRONT_END_URL}/integration/fail"
