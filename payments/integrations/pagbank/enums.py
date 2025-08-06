from enum import Enum


class ChargePaymentStatus(Enum):
    # https://developer.pagbank.com.br/reference/objeto-charge
    AUTHORIZED = "AUTHORIZED"
    PAID = "PAID"
    IN_ANALYSIS = "IN_ANALYSIS"
    DECLINED = "DECLINED"
    CANCELED = "CANCELED"
    WAITING = "WAITING"


class QRCodeLinkTypes(Enum):
    PNG = "QRCODE.PNG"
    BASE64 = "QRCODE.BASE64"


class SplitMethods(Enum):
    FIXED = "FIXED"
    PERCENTAGE = "PERCENTAGE"
