from django.urls import include, path
from rest_framework import routers

app_name = "payments"


router = routers.SimpleRouter()


urlpatterns = [
    path(
        "integrations/",
        include(
            "payments.integrations.urls",
            namespace="integrations",
        ),
    ),
    path("", include(router.urls)),
]
