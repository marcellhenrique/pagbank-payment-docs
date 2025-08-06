class PaymentGatewayError(Exception):
    def __init__(self, message: str = "An unexpected error has ocurred") -> None:
        self.message = message

    def __str__(self) -> str:
        return self.message


class PaymentGatewayClientNotFoundError(PaymentGatewayError):
    def __init__(self, message: str = "A payment gateway with this name was not found"):
        self.message = message

        super().__init__(message)


class PaymentGatewayClientRequestFailedError(PaymentGatewayError):
    def __init__(self, message: str = "The request to the payment gateway failed"):
        self.message = message

        super().__init__(message)
