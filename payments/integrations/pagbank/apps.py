from django.apps import AppConfig


class PagBankIntegrationConfigConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "payments.integrations.pagbank"
