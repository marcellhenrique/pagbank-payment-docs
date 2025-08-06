# PagBank Models Reference

## Overview

This document provides comprehensive documentation for all PagBank-related Django models, including their fields, methods, relationships, and usage patterns.

## Core Models

### PagBankPublicKey

Manages public keys used for credit card encryption in PagBank transactions.

#### Model Definition

```python
class PagBankPublicKey(models.Model):
    key = models.CharField(_("Key"), max_length=512)
    created_at = models.DateTimeField(_("Created at"))
    expires_at = models.DateTimeField(
        _("Expires at"),
        default=generate_default_expiration,
    )
    
    valid_objects = PagBankPublicKeyManager()
    objects = PagBankPublicKeyManager(include_expired=True)
```

#### Fields

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `key` | CharField | The public key string | max_length=512, required |
| `created_at` | DateTimeField | When the key was created | required |
| `expires_at` | DateTimeField | When the key expires | default=6 months from creation |

#### Properties

##### `expired` (Property)

Returns whether the public key has expired.

```python
@property
def expired(self):
    return self.expires_at <= timezone.now()

@expired.setter
def expired(self, __):
    return  # Read-only property
```

**Usage**:
```python
key = PagBankPublicKey.objects.first()
if key.expired:
    print("Key has expired")
```

#### Managers

##### `valid_objects` (PagBankPublicKeyManager)

Manager that returns only non-expired keys.

```python
# Get only valid (non-expired) keys
valid_keys = PagBankPublicKey.valid_objects.all()
latest_key = PagBankPublicKey.valid_objects.order_by("-created_at").first()
```

##### `objects` (PagBankPublicKeyManager)

Manager that returns all keys including expired ones.

```python
# Get all keys including expired
all_keys = PagBankPublicKey.objects.all()
expired_keys = PagBankPublicKey.objects.filter(expired=True)
```

#### Manager Methods

##### `create_from_api_response_data(**data)`

Creates a new public key from PagBank API response data.

```python
# API response data structure
response_data = {
    "public_key": "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQE...",
    "created_at": 1642176000000  # timestamp in milliseconds
}

# Create key from API response
key = PagBankPublicKey.valid_objects.create_from_api_response_data(**response_data)
```

#### Meta Options

```python
class Meta:
    ordering = ["-id"]
    verbose_name = _("PagBank public key")
    verbose_name_plural = _("PagBank public keys")
```

#### Usage Examples

```python
# Create a new public key
key = PagBankPublicKey.objects.create(
    key="MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQE...",
    created_at=timezone.now()
)

# Get the latest valid key
latest_key = PagBankPublicKey.valid_objects.order_by("-created_at").first()

# Check if key is expired
if latest_key and not latest_key.expired:
    print(f"Using valid key: {latest_key.key[:20]}...")

# Get expired keys for cleanup
expired_keys = PagBankPublicKey.objects.filter(expired=True)
```

---

### PagBankConnectAuthorization

Stores OAuth authorization information for PagBank Connect marketplace integration.

#### Model Definition

```python
class PagBankConnectAuthorization(models.Model):
    scope = models.CharField(_("Scope"), max_length=150)
    account_id = models.CharField(_("Account id"), max_length=255)
```

#### Fields

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `scope` | CharField | OAuth authorization scope | max_length=150, required |
| `account_id` | CharField | PagBank account identifier | max_length=255, required |

#### Meta Options

```python
class Meta:
    ordering = ["-id"]
    verbose_name = _("PagBank Connect Authorization")
    verbose_name_plural = _("PagBank Connect Authorizations")
```

#### String Representation

```python
def __str__(self) -> str:
    return f"{self.account_id}"
```

#### Usage Examples

```python
# Create authorization record
auth = PagBankConnectAuthorization.objects.create(
    scope="accounts.read payments.refund payments.split.read",
    account_id="ACCO_123456789ABCDEF"
)

# Find authorization by account ID
auth = PagBankConnectAuthorization.objects.get(account_id="ACCO_123456789ABCDEF")

# Check authorization scope
if "payments.refund" in auth.scope:
    print("Refund permission granted")
```

---

## Related Order Models

### Order

Main order model that integrates with PagBank.

#### Key Fields for PagBank Integration

| Field | Type | Description |
|-------|------|-------------|
| `reference_id` | UUIDField | Unique order identifier (primary key) |
| `external_id` | CharField | PagBank order ID (set after creation) |
| `customer` | OneToOneField | Customer information |
| `payment_gateway` | CharField | Set to "PAGBANK" |

#### Relationships

```python
# Related models accessed through order
order.charges.all()        # OrderCharge instances
order.items.all()         # OrderItem instances  
order.qr_codes.all()      # OrderQRCode instances (for PIX)
order.splits.all()        # OrderSplit instances (for marketplace)
```

#### Usage with PagBank

```python
from payments.integrations.enums import PaymentGatewayIntegrations

# Create order for PagBank
order = Order.objects.create(
    customer=customer,
    payment_gateway=PaymentGatewayIntegrations.PAGBANK
)

# After processing with PagBank API
order.external_id = "ORDER_123456789"  # Set by PagBank
order.save()
```

---

### OrderCharge

Represents a payment charge within an order.

#### Key Fields for PagBank Integration

| Field | Type | Description |
|-------|------|-------------|
| `external_id` | CharField | PagBank charge ID |
| `status` | CharField | Payment status |
| `value` | IntegerField | Amount in cents |
| `currency` | CharField | Currency code (BRL) |
| `paid_at` | DateTimeField | Payment completion time |
| `canceled_at` | DateTimeField | Cancellation time |
| `cancel_status` | CharField | Cancellation status |

#### Status Choices

```python
class Status(models.TextChoices):
    CREATED = "CREATED"
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    AUTHORIZED = "AUTHORIZED"
    PAID = "PAID"
    DECLINED = "DECLINED"
    CANCELED = "CANCELED"
    FAILED = "FAILED"
```

#### Cancel Status Choices

```python
class CancelStatus(models.TextChoices):
    PENDING = "PENDING"
    CANCELED = "CANCELED"
    FAILED = "FAILED"
```

#### Relationships

```python
charge.order              # Parent order
charge.payment_method     # OrderChargePaymentMethod
charge.to_trip_contract_charge.all()  # Trip contract relationships
```

#### Usage Examples

```python
# Create charge for PagBank order
charge = OrderCharge.objects.create(
    order=order,
    reference_id="charge_123",
    description="Payment for trip booking",
    value=10000,  # R$ 100.00
    currency="BRL"
)

# Update status from webhook
charge.status = OrderCharge.Status.PAID
charge.paid_at = timezone.now()
charge.save()

# Cancel charge
charge.status = OrderCharge.Status.CANCELED
charge.cancel_status = OrderCharge.CancelStatus.CANCELED
charge.canceled_at = timezone.now()
charge.save()
```

---

### OrderChargePaymentMethod

Stores payment method information for charges.

#### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `charge` | OneToOneField | Related charge |
| `type` | CharField | Payment method type |
| `installments` | IntegerField | Number of installments |

#### Type Choices

```python
class Types(models.TextChoices):
    CREDIT_CARD = "CREDIT_CARD"
    PIX = "PIX"
```

#### Related Models

- `OrderChargePaymentMethodCard`: Credit card details
- `OrderChargePaymentMethodPIX`: PIX payment details

---

### OrderChargePaymentMethodCard

Credit card payment method details.

#### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `payment_method` | OneToOneField | Parent payment method |
| `card_token` | CharField | Encrypted card token |
| `brand` | CharField | Card brand (Visa, Mastercard, etc.) |
| `first_digits` | CharField | First 6 digits |
| `last_digits` | CharField | Last 4 digits |
| `exp_month` | CharField | Expiration month |
| `exp_year` | CharField | Expiration year |
| `holder_name` | CharField | Cardholder name |
| `holder_document` | CharField | Cardholder document |

---

### OrderChargePaymentMethodPIX

PIX payment method details.

#### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `payment_method` | OneToOneField | Parent payment method |
| `holder_name` | CharField | PIX account holder name |
| `holder_document` | CharField | PIX account holder document |

---

### OrderQRCode

QR code information for PIX payments.

#### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `order` | ForeignKey | Related order |
| `external_id` | CharField | PagBank QR code ID |
| `amount` | IntegerField | QR code amount in cents |
| `text` | TextField | PIX copy-paste text |
| `png_link` | URLField | PNG image URL |
| `base64_link` | URLField | Base64 image URL |
| `expiration` | DateTimeField | QR code expiration |

#### Usage Examples

```python
# Create QR code for PIX payment
qr_code = OrderQRCode.objects.create(
    order=order,
    amount=10000,  # R$ 100.00
    expiration=timezone.now() + timedelta(hours=1)
)

# After PagBank API call, fields are populated:
# qr_code.external_id = "QRCO_123456789"
# qr_code.text = "00020126580014br.gov.bcb.pix..."
# qr_code.png_link = "https://api.pagbank.com/qr-codes/123/png"
# qr_code.base64_link = "https://api.pagbank.com/qr-codes/123/base64"
```

---

### OrderSplit

Revenue splitting configuration for marketplace scenarios.

#### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `order` | ForeignKey | Related order |
| `account_external_id` | CharField | PagBank account ID |
| `percentage` | DecimalField | Split percentage |
| `is_platform` | BooleanField | Whether this is the platform fee |

#### Manager

```python
# Custom manager for split operations
class OrderSplitManager(models.Manager):
    def for_order(self, order):
        return self.filter(order=order)
```

#### Usage Examples

```python
# Create split configuration
platform_split = OrderSplit.objects.create(
    order=order,
    account_external_id="ACCO_PLATFORM_123",
    percentage=5.00,  # 5% platform fee
    is_platform=True
)

seller_split = OrderSplit.objects.create(
    order=order,
    account_external_id="ACCO_SELLER_456",
    percentage=95.00,  # 95% to seller
    is_platform=False
)
```

---

### Customer

Customer information for PagBank orders.

#### Key Fields for PagBank

| Field | Type | Description |
|-------|------|-------------|
| `external_id` | CharField | PagBank customer ID |
| `name` | CharField | Customer full name |
| `email` | EmailField | Customer email |
| `document` | CharField | CPF/CNPJ document |
| `address` | OneToOneField | Customer address |

#### Related Models

- `Phone`: Customer phone number
- `Address`: Customer address information

---

### Phone

Customer phone number information.

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `customer` | OneToOneField | Related customer |
| `country_code` | CharField | Country code (55 for Brazil) |
| `area_code` | CharField | Area code |
| `number` | CharField | Phone number |

---

### Address

Customer address information.

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `state` | CharField | State |
| `city` | CharField | City |
| `district` | CharField | District/neighborhood |
| `street` | CharField | Street name |
| `number` | CharField | Street number |
| `zip_code` | CharField | ZIP/postal code |
| `additional_info` | CharField | Additional info (optional) |

---

## Model Relationships Diagram

```
Order (1) ←→ (1) Customer
  ↓
OrderCharge (N) ←→ (1) OrderChargePaymentMethod
  ↓                    ↓
OrderItem (N)     OrderChargePaymentMethodCard (0..1)
  ↓                    ↓
OrderQRCode (N)   OrderChargePaymentMethodPIX (0..1)
  ↓
OrderSplit (N)

Customer (1) ←→ (1) Phone
Customer (1) ←→ (1) Address

PagBankPublicKey (independent)
PagBankConnectAuthorization (independent)
```

---

## Database Queries

### Common Query Patterns

#### Get Valid Public Key

```python
# Get the most recent valid public key
key = PagBankPublicKey.valid_objects.order_by("-created_at").first()
```

#### Find Order by External ID

```python
# Find order by PagBank external ID
order = Order.objects.get(external_id="ORDER_123456789")
```

#### Get Paid Charges

```python
# Get all paid charges
paid_charges = OrderCharge.objects.filter(status=OrderCharge.Status.PAID)
```

#### Get PIX Orders with QR Codes

```python
# Get orders with PIX payment and QR codes
pix_orders = Order.objects.filter(
    payment_gateway=PaymentGatewayIntegrations.PAGBANK,
    qr_codes__isnull=False
).prefetch_related('qr_codes')
```

#### Get Orders with Splits

```python
# Get marketplace orders with revenue splits
split_orders = Order.objects.filter(
    splits__isnull=False
).prefetch_related('splits')
```

### Performance Optimizations

#### Select Related

```python
# Optimize queries with select_related
orders = Order.objects.select_related(
    'customer',
    'customer__phone',
    'customer__address'
).prefetch_related(
    'charges__payment_method__card',
    'charges__payment_method__pix',
    'qr_codes',
    'splits'
)
```

#### Bulk Operations

```python
# Bulk update charge statuses
OrderCharge.objects.filter(
    external_id__in=charge_ids
).update(
    status=OrderCharge.Status.PAID,
    paid_at=timezone.now()
)
```

---

## Model Validation

### Custom Validators

```python
from django.core.exceptions import ValidationError

def validate_cpf(value):
    """Validate Brazilian CPF document"""
    if not re.match(r'^\d{11}$', value):
        raise ValidationError('CPF must have 11 digits')

class Customer(TimeStampedModel):
    document = models.CharField(
        _("Document"),
        max_length=14,
        validators=[validate_cpf]
    )
```

### Model Clean Methods

```python
class OrderCharge(TimeStampedModel):
    def clean(self):
        if self.value <= 0:
            raise ValidationError('Charge value must be positive')
        
        if self.currency != 'BRL':
            raise ValidationError('Only BRL currency is supported')
```

---

## Signals and Hooks

### Post-Save Signals

```python
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=OrderCharge)
def charge_status_changed(sender, instance, created, **kwargs):
    if not created and instance.status == OrderCharge.Status.PAID:
        # Send notification when charge is paid
        send_payment_confirmation.delay(instance.id)
```

### Pre-Delete Signals

```python
@receiver(pre_delete, sender=PagBankPublicKey)
def cleanup_expired_keys(sender, instance, **kwargs):
    # Log key deletion
    logger.info(f"Deleting public key: {instance.id}")
```

---

## Testing Models

### Model Tests

```python
from django.test import TestCase
from django.utils import timezone

class PagBankPublicKeyTest(TestCase):
    def test_key_expiration(self):
        # Test key expiration logic
        past_date = timezone.now() - timedelta(days=1)
        key = PagBankPublicKey.objects.create(
            key="test_key",
            created_at=timezone.now(),
            expires_at=past_date
        )
        
        self.assertTrue(key.expired)
    
    def test_valid_objects_manager(self):
        # Test manager filtering
        expired_key = PagBankPublicKey.objects.create(
            key="expired_key",
            created_at=timezone.now(),
            expires_at=timezone.now() - timedelta(days=1)
        )
        
        valid_key = PagBankPublicKey.objects.create(
            key="valid_key",
            created_at=timezone.now()
        )
        
        valid_keys = PagBankPublicKey.valid_objects.all()
        self.assertIn(valid_key, valid_keys)
        self.assertNotIn(expired_key, valid_keys)
```

### Factory Classes

```python
import factory
from factory.django import DjangoModelFactory

class PagBankPublicKeyFactory(DjangoModelFactory):
    class Meta:
        model = PagBankPublicKey
    
    key = factory.Faker('uuid4')
    created_at = factory.LazyFunction(timezone.now)

class OrderFactory(DjangoModelFactory):
    class Meta:
        model = Order
    
    customer = factory.SubFactory(CustomerFactory)
    payment_gateway = PaymentGatewayIntegrations.PAGBANK
```

---

## Migration Considerations

### Adding Fields

```python
# When adding new fields, consider backwards compatibility
class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name='pagbankpublickey',
            name='version',
            field=models.CharField(max_length=10, default='v1'),
        ),
    ]
```

### Data Migrations

```python
def migrate_external_ids(apps, schema_editor):
    """Migrate legacy external IDs to new format"""
    Order = apps.get_model('payments', 'Order')
    
    for order in Order.objects.filter(external_id__startswith='OLD_'):
        order.external_id = order.external_id.replace('OLD_', 'ORDER_')
        order.save()

class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(migrate_external_ids),
    ]
```

---

## Best Practices

### Model Design

1. **Use appropriate field types** for data validation
2. **Add database indexes** for frequently queried fields
3. **Use related_name** for reverse relationships
4. **Implement proper string representations** for debugging
5. **Add model-level validation** in clean() methods

### Performance

1. **Use select_related()** for foreign key relationships
2. **Use prefetch_related()** for many-to-many relationships
3. **Add database indexes** on filtered fields
4. **Use bulk operations** for mass updates
5. **Consider caching** for frequently accessed data

### Security

1. **Validate sensitive data** at the model level
2. **Use encrypted fields** for sensitive information
3. **Implement proper permissions** for model access
4. **Log model changes** for audit trails
5. **Sanitize data** before database operations