from typing import Unpack

from django.utils.translation import gettext_lazy as _

from companies.models import Company
from core.mails import Mail
from currencies.models import CurrencyHistory
from payments.orders.models import OrderCharge, OrderChargePaymentMethod
from payments.typing import MailUpdatePaymentStatusDTO
from trips.models import TripContractCharge, TripContractChargePaymentRelation

TEMPLATE_PATH_TYPE_MAPPING = {
    OrderChargePaymentMethod.Types.CREDIT_CARD: "payments/credit_card_payment_status_update.html",
    OrderChargePaymentMethod.Types.PIX: "payments/pix_payment_status_update.html",
}


def mail_payment_status_update(
    **kwargs: Unpack[MailUpdatePaymentStatusDTO],
):
    company = Company.objects.get(pk=kwargs.get("company_pk"))
    charge = OrderCharge.objects.get(pk=kwargs.get("charge_pk"))

    charge_relation: TripContractChargePaymentRelation = (
        charge.to_trip_contract_charge.first()
    )
    trip_contract_charge: TripContractCharge = charge_relation.trip_contract_charge
    historical_currency: CurrencyHistory = (
        trip_contract_charge.order.historical_currency
    )

    payment_method: OrderChargePaymentMethod = charge.payment_method
    template_path = TEMPLATE_PATH_TYPE_MAPPING[payment_method.type]

    mail = Mail(
        language=kwargs.get("language"),
        template_path=template_path,
        subject=_("Payment status update"),
        context={
            "company": company,
            "charge": charge,
            "historical_currency": historical_currency,
        },
    )
    mail.subject = mail.translate(mail.subject)
    mail.send(kwargs.get("email"))
