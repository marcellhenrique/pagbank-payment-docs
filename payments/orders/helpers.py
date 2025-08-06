from dateutil.relativedelta import relativedelta as rdelta
from django.utils import timezone


def get_default_qr_code_expiration():
    return timezone.now() + rdelta(days=1)
