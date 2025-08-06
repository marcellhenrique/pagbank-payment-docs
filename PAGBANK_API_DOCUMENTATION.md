# PagBank Payment Gateway Integration - API Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [API Client](#api-client)
5. [Models](#models)
6. [Serializers](#serializers)
7. [Views & Endpoints](#views--endpoints)
8. [Webhooks](#webhooks)
9. [Authentication](#authentication)
10. [Configuration](#configuration)
11. [Usage Examples](#usage-examples)
12. [Error Handling](#error-handling)
13. [Testing](#testing)

---

## Overview

The PagBank Payment Gateway Integration provides a comprehensive solution for processing payments through PagBank's API. This integration supports:

- **Credit Card Payments**: Secure credit card processing with tokenization
- **PIX Payments**: Brazil's instant payment system with QR code generation
- **Webhook Handling**: Real-time payment status updates
- **OAuth Authorization**: Secure account linking for marketplace operations
- **Payment Splitting**: Revenue sharing between multiple accounts

### Key Features

- ✅ Credit card and PIX payment processing
- ✅ Public key management for secure transactions
- ✅ Webhook authentication and processing
- ✅ OAuth 2.0 integration for account authorization
- ✅ Payment cancellation and refunds
- ✅ Revenue splitting for marketplace scenarios
- ✅ Comprehensive logging and error handling

---

## Architecture

The integration follows a layered architecture:

```
┌─────────────────────────────────────────┐
│                 Views                   │ ← API Endpoints
├─────────────────────────────────────────┤
│               Serializers               │ ← Data Validation & Transformation
├─────────────────────────────────────────┤
│                Client                   │ ← PagBank API Communication
├─────────────────────────────────────────┤
│                Models                   │ ← Data Persistence
├─────────────────────────────────────────┤
│               Webhooks                  │ ← Real-time Updates
└─────────────────────────────────────────┘
```

---

## Core Components

### File Structure

```
payments/integrations/pagbank/
├── client.py              # Main API client
├── models.py              # Database models
├── serializers.py         # Data serialization
├── views.py               # API endpoints
├── enums.py               # Constants and enums
├── constants.py           # Configuration constants
├── helpers.py             # Utility functions
├── managers.py            # Database managers
├── tasks.py               # Async tasks
├── urls.py                # URL patterns
└── webhooks/
    ├── views.py           # Webhook endpoints
    ├── serializers.py     # Webhook data handling
    ├── authentication_classes.py  # Webhook security
    └── helpers.py         # Webhook utilities
```

---

## API Client

### PagBankClient Class

The main client class for interacting with PagBank's API.

```python
from payments.integrations.pagbank.client import PagBankClient

client = PagBankClient()
```

#### Configuration

The client automatically configures itself using Django settings:

```python
# Required settings
PAGBANK_API_TOKEN = "your_api_token"
PAGBANK_API_URL = "https://api.pagbank.com"
PAGBANK_WEBHOOK_API_KEYS = "your_webhook_key"

# OAuth settings (for marketplace)
PAGBANK_APP_CLIENT_ID = "your_client_id"
PAGBANK_APP_CLIENT_SECRET = "your_client_secret"
PAGBANK_CONNECT_BASE_URL = "https://connect.pagbank.com"
```

#### Methods

##### `get_public_key() -> str`

Retrieves or creates a public key for secure transactions.

```python
client = PagBankClient()
public_key = client.get_public_key()
```

**Returns**: String containing the public key
**Raises**: `PaymentGatewayClientRequestFailedError` if request fails

##### `create_credit_card_order(order: Order) -> requests.Response`

Creates a credit card payment order.

```python
response = client.create_credit_card_order(order)
```

**Parameters**:
- `order`: Order instance with payment details

**Returns**: HTTP response from PagBank API
**Side Effects**: Updates order and charge status in database

##### `create_pix_order(order: Order) -> requests.Response`

Creates a PIX payment order with QR code.

```python
response = client.create_pix_order(order)
```

**Parameters**:
- `order`: Order instance with PIX payment details

**Returns**: HTTP response with QR code information
**Side Effects**: Updates order with QR code links

##### `cancel_payment(charge: OrderCharge, company: Company) -> requests.Response`

Cancels an existing payment.

```python
response = client.cancel_payment(charge, company)
```

**Parameters**:
- `charge`: OrderCharge instance to cancel
- `company`: Company instance for notification

**Returns**: HTTP response or None if cancellation fails
**Side Effects**: Updates charge status and sends notification email

##### `update_pix_order(request: Request, order: Order, data: dict) -> DRFResponse`

Updates PIX order status from webhook data.

```python
response = client.update_pix_order(request, order, webhook_data)
```

**Parameters**:
- `request`: Django REST Framework request
- `order`: Order instance to update
- `data`: Webhook payload data

**Returns**: DRF Response with status code
**Side Effects**: Updates order status and sends notifications

---

## Models

### PagBankPublicKey

Manages public keys for secure transactions.

```python
from payments.integrations.pagbank.models import PagBankPublicKey

# Get valid public key
key = PagBankPublicKey.valid_objects.order_by("-created_at").first()
```

#### Fields

- `key`: CharField - The public key string (max 512 chars)
- `created_at`: DateTimeField - Creation timestamp
- `expires_at`: DateTimeField - Expiration timestamp (default: 6 months)

#### Properties

- `expired`: Boolean - Whether the key has expired

#### Managers

- `valid_objects`: Returns only non-expired keys
- `objects`: Returns all keys including expired ones

### PagBankConnectAuthorization

Stores OAuth authorization information for marketplace accounts.

```python
from payments.integrations.pagbank.models import PagBankConnectAuthorization

auth = PagBankConnectAuthorization.objects.create(
    scope="payments.read payments.write",
    account_id="ACCO_123456789"
)
```

#### Fields

- `scope`: CharField - Authorization scope (max 150 chars)
- `account_id`: CharField - PagBank account ID (max 255 chars)

---

## Serializers

### Request Serializers (Outgoing Data)

#### PagBankOrderSerializer

Serializes order data for PagBank API requests.

```python
from payments.integrations.pagbank.serializers import PagBankOrderSerializer

serializer = PagBankOrderSerializer(order)
pagbank_data = serializer.data
```

**Fields**:
- `reference_id`: Order reference ID
- `customer`: Customer information
- `items`: Order items
- `charges`: Payment charges

#### PagBankPixOrderSerializer

Specialized serializer for PIX orders.

```python
serializer = PagBankPixOrderSerializer(order)
pix_data = serializer.data
```

**Additional Fields**:
- `qr_codes`: QR code information
- `notification_urls`: Webhook URLs

### Response Serializers (Incoming Data)

#### PagBankOrderCreditCardPaymentResponseSerializer

Handles credit card payment responses.

```python
serializer = PagBankOrderCreditCardPaymentResponseSerializer(
    order, 
    data=response.json()
)
serializer.is_valid(raise_exception=True)
serializer.save()
```

#### PagBankPixOrderResponseSerializer

Handles PIX payment responses.

```python
serializer = PagBankPixOrderResponseSerializer(
    order,
    data=response.json()
)
serializer.is_valid(raise_exception=True)
serializer.save()
```

---

## Views & Endpoints

### Public Key Management

#### GET `/api/payments/integrations/pagbank/public-keys/`

Retrieves the current public key for frontend encryption.

**Permissions**: `AllowAny`
**Response**:
```json
{
    "key": "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQE..."
}
```

**Error Response**:
```json
{
    "detail": "An error has occurred"
}
```

### OAuth Authorization

#### POST `/api/payments/integrations/pagbank/request-authorization/`

Initiates OAuth authorization flow for marketplace integration.

**Permissions**: `IsValidVersion`, `IsCompanyUser`, `CanRequestPaymentGatewayAuthorization`
**Response**:
```json
{
    "authorization_url": "https://connect.pagbank.com/oauth2/authorize?..."
}
```

#### GET `/api/payments/integrations/pagbank/confirm-authorization/`

Handles OAuth callback and completes authorization.

**Permissions**: `AllowAny`
**Parameters**:
- `code`: Authorization code from PagBank
- `state`: State parameter for security

**Response**: Redirects to success or failure URL

#### POST `/api/payments/integrations/pagbank/disconnect-account/`

Disconnects PagBank account from company.

**Permissions**: `IsValidVersion`, `IsCompanyUser`, `CanRequestPaymentGatewayAuthorization`
**Response**: `204 No Content`

---

## Webhooks

### Webhook Endpoint

#### POST `/api/payments/integrations/pagbank/webhooks/orders/`

Receives payment status updates from PagBank.

**Authentication**: `PagBankTokenAuthentication` (production only)
**Headers**:
- `X-Product-Id`: Order external ID
- `X-Authenticity-Token`: Webhook signature

**Payload Example**:
```json
{
    "reference_id": "order_123",
    "charges": [
        {
            "id": "CHAR_123456789",
            "status": "PAID",
            "paid_at": "2024-01-15T10:30:00Z",
            "amount": {
                "value": 10000,
                "currency": "BRL"
            },
            "payment_method": {
                "type": "PIX",
                "pix": {
                    "holder": {
                        "name": "João Silva",
                        "document": "12345678901"
                    }
                }
            }
        }
    ]
}
```

### Webhook Authentication

The webhook authentication verifies request authenticity using HMAC signatures.

```python
from payments.integrations.pagbank.webhooks.authentication_classes import PagBankTokenAuthentication

# Authentication is automatically handled by the view
# Manual verification example:
from payments.integrations.pagbank.webhooks.helpers import generate_signature

expected_token = generate_signature(api_token, json_payload)
received_token = request.headers.get("X-Authenticity-Token")
is_valid = expected_token == received_token
```

---

## Authentication

### Webhook Authentication Class

```python
class PagBankTokenAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request: Request):
        token = request.headers.get("X-Authenticity-Token")
        expected_token = generate_signature(
            PagBankClient().get_api_token(),
            json.dumps(request.data, separators=(",", ":"))
        )
        
        if not token or (token != expected_token):
            raise AuthenticationFailed
            
        return (AnonymousUser, None)
```

---

## Configuration

### Required Django Settings

```python
# PagBank API Configuration
PAGBANK_API_TOKEN = "your_production_token"
PAGBANK_API_URL = "https://api.pagbank.com"
PAGBANK_WEBHOOK_API_KEYS = "your_webhook_key"

# OAuth Configuration (for marketplace)
PAGBANK_APP_CLIENT_ID = "your_app_client_id"
PAGBANK_APP_CLIENT_SECRET = "your_app_client_secret"
PAGBANK_CONNECT_BASE_URL = "https://connect.pagbank.com"

# Frontend URLs
FRONT_END_URL = "https://your-frontend.com"
API_URL = "https://your-api.com"
```

### Environment-Specific Settings

```python
# Development
PAGBANK_API_URL = "https://sandbox.api.pagbank.com"
PAGBANK_CONNECT_BASE_URL = "https://sandbox.connect.pagbank.com"

# Production
PAGBANK_API_URL = "https://api.pagbank.com"
PAGBANK_CONNECT_BASE_URL = "https://connect.pagbank.com"
```

---

## Usage Examples

### Creating a Credit Card Payment

```python
from payments.orders.models import Order, Customer, OrderItem, OrderCharge
from payments.integrations.pagbank.client import PagBankClient

# Create customer
customer = Customer.objects.create(
    name="João Silva",
    email="joao@example.com",
    document="12345678901"
)

# Create order
order = Order.objects.create(
    customer=customer,
    payment_gateway="PAGBANK"
)

# Add order items
OrderItem.objects.create(
    order=order,
    reference_id="item_1",
    name="Product Name",
    quantity=1,
    unit_amount=10000  # R$ 100.00 in cents
)

# Create charge with payment method
charge = OrderCharge.objects.create(
    order=order,
    reference_id="charge_1",
    description="Payment for order",
    value=10000,
    currency="BRL"
)

# Process payment
client = PagBankClient()
response = client.create_credit_card_order(order)
```

### Creating a PIX Payment

```python
from payments.orders.models import OrderQRCode

# Create QR code for PIX payment
qr_code = OrderQRCode.objects.create(
    order=order,
    amount=10000,
    expiration=timezone.now() + timedelta(hours=1)
)

# Process PIX payment
client = PagBankClient()
response = client.create_pix_order(order)

# QR code information will be available in the order
order.refresh_from_db()
qr_code = order.qr_codes.first()
print(f"PIX QR Code: {qr_code.text}")
print(f"QR Code PNG: {qr_code.png_link}")
```

### Canceling a Payment

```python
from companies.models import Company

company = Company.objects.get(id=1)
charge = OrderCharge.objects.get(external_id="CHAR_123456789")

client = PagBankClient()
response = client.cancel_payment(charge, company)

if response:
    print("Payment canceled successfully")
else:
    print("Payment cancellation failed")
```

### OAuth Authorization Flow

```python
from payments.integrations.pagbank.helpers import get_app_authorization_request_url

# Step 1: Generate authorization URL
company = Company.objects.get(id=1)
auth_url = get_app_authorization_request_url(company)

# Step 2: Redirect user to auth_url
# Step 3: Handle callback in PagBankAuthorizationRedirectionView
# Step 4: Authorization completed via async task
```

---

## Error Handling

### Custom Exceptions

```python
from payments.exceptions import PaymentGatewayClientRequestFailedError

try:
    client = PagBankClient()
    public_key = client.get_public_key()
except PaymentGatewayClientRequestFailedError as e:
    logger.error(f"PagBank API error: {e}")
    # Handle error appropriately
```

### HTTP Status Codes

| Status Code | Description | Action |
|-------------|-------------|---------|
| 200 | Success | Process response data |
| 400 | Bad Request | Validate request data |
| 401 | Unauthorized | Check API credentials |
| 404 | Not Found | Verify resource exists |
| 500 | Server Error | Retry with backoff |

### Webhook Error Handling

```python
# Webhook validation errors return 400 Bad Request
# Authentication errors return 401 Unauthorized
# Processing errors are logged but return 204 No Content
```

---

## Testing

### Unit Tests

```python
from django.test import TestCase
from payments.integrations.pagbank.client import PagBankClient
from payments.integrations.pagbank.models import PagBankPublicKey

class PagBankClientTest(TestCase):
    def setUp(self):
        self.client = PagBankClient()
    
    def test_get_public_key(self):
        # Create a valid public key
        key = PagBankPublicKey.valid_objects.create(
            key="test_key",
            created_at=timezone.now()
        )
        
        result = self.client.get_existing_public_key_from_db()
        self.assertEqual(result, key)
    
    def test_create_credit_card_order(self):
        # Test order creation
        order = self.create_test_order()
        response = self.client.create_credit_card_order(order)
        self.assertEqual(response.status_code, 200)
```

### Integration Tests

```python
class PagBankIntegrationTest(TestCase):
    def test_webhook_processing(self):
        # Test webhook endpoint
        webhook_data = {
            "reference_id": "test_order",
            "charges": [...]
        }
        
        response = self.client.post(
            "/api/payments/integrations/pagbank/webhooks/orders/",
            data=webhook_data,
            content_type="application/json",
            HTTP_X_PRODUCT_ID="ORDER_123"
        )
        
        self.assertEqual(response.status_code, 204)
```

### Mock Testing

```python
from unittest.mock import patch, Mock

class PagBankMockTest(TestCase):
    @patch('payments.integrations.pagbank.client.requests.post')
    def test_create_public_key(self, mock_post):
        # Mock PagBank API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "public_key": "test_key",
            "created_at": 1642176000000
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        client = PagBankClient()
        response = client.create_public_key()
        
        self.assertEqual(response, mock_response)
```

---

## Enums and Constants

### ChargePaymentStatus

```python
from payments.integrations.pagbank.enums import ChargePaymentStatus

# Available statuses
ChargePaymentStatus.AUTHORIZED    # Payment authorized
ChargePaymentStatus.PAID          # Payment completed
ChargePaymentStatus.IN_ANALYSIS   # Under analysis
ChargePaymentStatus.DECLINED      # Payment declined
ChargePaymentStatus.CANCELED      # Payment canceled
ChargePaymentStatus.WAITING       # Waiting for payment
```

### QRCodeLinkTypes

```python
from payments.integrations.pagbank.enums import QRCodeLinkTypes

QRCodeLinkTypes.PNG     # PNG image link
QRCodeLinkTypes.BASE64  # Base64 encoded image
```

### SplitMethods

```python
from payments.integrations.pagbank.enums import SplitMethods

SplitMethods.FIXED      # Fixed amount split
SplitMethods.PERCENTAGE # Percentage-based split
```

---

## Best Practices

### Security

1. **Always validate webhook signatures** in production
2. **Use HTTPS** for all API communications
3. **Store API tokens securely** using environment variables
4. **Implement rate limiting** for public endpoints
5. **Log all API interactions** for audit trails

### Performance

1. **Cache public keys** to reduce API calls
2. **Use async tasks** for webhook processing
3. **Implement retry logic** with exponential backoff
4. **Monitor API response times** and set appropriate timeouts

### Error Handling

1. **Implement comprehensive logging** for debugging
2. **Use custom exceptions** for better error categorization
3. **Provide meaningful error messages** to users
4. **Implement circuit breakers** for external API calls

### Data Management

1. **Keep sensitive data encrypted** at rest
2. **Implement data retention policies** for compliance
3. **Use database transactions** for atomic operations
4. **Validate all input data** before processing

---

## Support and Troubleshooting

### Common Issues

1. **Public Key Expiration**: Keys expire after 6 months - implement automatic renewal
2. **Webhook Authentication**: Ensure webhook signatures are properly validated
3. **OAuth Flow**: Handle state parameter correctly to prevent CSRF attacks
4. **Payment Status**: Monitor payment status changes through webhooks

### Debugging

1. **Check API logs** for request/response details
2. **Verify webhook signatures** manually if authentication fails
3. **Test with PagBank sandbox** before production deployment
4. **Monitor Sentry** for exception tracking

### Contact Information

- **PagBank Developer Documentation**: https://developer.pagbank.com.br/
- **PagBank Support**: Contact through your PagBank account
- **Internal Support**: Check project documentation and team contacts

---

*Last updated: 2024*
*Version: 1.0*