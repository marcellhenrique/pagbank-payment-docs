from django.urls import include, path
from rest_framework import routers

app_name = "integrations"


router = routers.SimpleRouter()


urlpatterns = [
    path(
        "pagbank/",
        include(
            "payments.integrations.pagbank.urls",
            namespace="pagbank",
        ),
    ),
    path("", include(router.urls)),
]
