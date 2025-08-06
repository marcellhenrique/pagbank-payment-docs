from typing import Unpack

from django.db.models import BooleanField, Case, Manager, Value, When
from django.db.models.query import QuerySet
from django.utils import timezone

from payments.helpers import convert_timestamp_ms_to_datetime
from payments.integrations.pagbank.typing import PagBankPublicKeyResponse


class PagBankPublicKeyManager(Manager):
    def __init__(self, include_expired=False) -> None:
        self.include_expired = include_expired
        super().__init__()

    def get_queryset(self) -> QuerySet:
        qs = (
            super()
            .get_queryset()
            .annotate(
                expired=Case(
                    When(expires_at__lte=timezone.now(), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
            )
        )

        if not self.include_expired:
            return qs.filter(expired=False)

        return qs

    def create_from_api_response_data(self, **data: Unpack[PagBankPublicKeyResponse]):
        response_data_model_mapping = {
            "key": data["public_key"],
            "created_at": convert_timestamp_ms_to_datetime(data["created_at"]),
        }

        return self.create(**response_data_model_mapping)
