from django.db import models


class PaymentGatewayIntegrations(models.TextChoices):
    PAGBANK = "PAGBANK"
