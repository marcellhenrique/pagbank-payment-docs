from django.urls import path

from payments.integrations.pagbank.webhooks.views import PagBankOrderWebHook

app_name = "webhooks"


urlpatterns = [
    path("orders/", PagBankOrderWebHook.as_view(), name="orders"),
]
