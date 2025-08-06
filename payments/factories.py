from payments.exceptions import PaymentGatewayClientNotFoundError
from payments.integrations.enums import PaymentGatewayIntegrations
from payments.integrations.pagbank.client import PagBankClient

GATEWAYS_MAPPING = {
    PaymentGatewayIntegrations.PAGBANK: PagBankClient,
}


class PaymentGatewayClientFactory:
    def __init__(self, name: str) -> None:
        if name not in GATEWAYS_MAPPING:
            raise PaymentGatewayClientNotFoundError

        self.name = name

    def get_client(self):
        return GATEWAYS_MAPPING[self.name]()
