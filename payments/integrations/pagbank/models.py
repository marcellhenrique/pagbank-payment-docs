from dateutil.relativedelta import relativedelta as rdelta
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from payments.integrations.pagbank.managers import PagBankPublicKeyManager


def generate_default_expiration():
    return timezone.now() + rdelta(months=6)


class PagBankPublicKey(models.Model):
    key = models.CharField(_("Key"), max_length=512)
    created_at = models.DateTimeField(_("Created at"))
    expires_at = models.DateTimeField(
        _("Expires at"),
        default=generate_default_expiration,
    )

    valid_objects = PagBankPublicKeyManager()
    objects = PagBankPublicKeyManager(include_expired=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = _("PagBank public key")
        verbose_name_plural = _("PagBank public keys")

    def __str__(self) -> str:
        return super().__str__()

    @property
    def expired(self):
        return self.expires_at <= timezone.now()

    @expired.setter
    def expired(self, __):
        return


class PagBankConnectAuthorization(models.Model):
    scope = models.CharField(_("Scope"), max_length=150)
    account_id = models.CharField(_("Account id"), max_length=255)

    class Meta:
        ordering = ["-id"]
        verbose_name = _("PagBank Connect Authorization")
        verbose_name_plural = _("PagBank Connect Authorizations")

    def __str__(self) -> str:
        return f"{self.account_id}"
