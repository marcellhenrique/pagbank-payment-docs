from abc import ABC, abstractmethod

from companies.models import Company
from payments.orders.models import Order, OrderCharge


class BasePaymentGatewayClient(ABC):
    request_timeout = 60

    @abstractmethod
    def create_credit_card_order(self, order: Order):
        pass

    @abstractmethod
    def create_pix_order(self, order: Order):
        pass

    @abstractmethod
    def cancel_payment(self, charge: OrderCharge, company: Company):
        pass
