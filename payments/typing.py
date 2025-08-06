from typing import TypedDict
from uuid import UUID


class MailUpdatePaymentStatusDTO(TypedDict):
    company_pk: int
    language: str
    charge_pk: UUID
    email: str
