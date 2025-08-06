# PagBank Client API Reference

## Overview

The `PagBankClient` class is the main interface for communicating with PagBank's payment API. It inherits from `BasePaymentGatewayClient` and provides methods for payment processing, public key management, and order handling.

## Class Definition

```python
class PagBankClient(BasePaymentGatewayClient):
    """
    Client to interact with the PagBank API, handling public key creation and management.
    """
    
    MAX_RETRIES = 5
    PUBLIC_KEYS_ENDPOINT = "/public-keys"
    CHANGE_PUBLIC_KEY_ENDPOINT = "/public-keys/card"
    ORDER_ENDPOINT = "/orders"
    CANCEL_CHARGES_ENDPOINT = "/charges/{charge_id}/cancel"
```

## Constructor

### `__init__(self) -> None`

Initializes the PagBank client with API configuration.

**Attributes Set**:
- `api_url`: PagBank API base URL
- `api_token`: Authentication token
- `request_timeout`: HTTP request timeout (30 seconds)

**Example**:
```python
from payments.integrations.pagbank.client import PagBankClient

client = PagBankClient()
print(f"API URL: {client.api_url}")
print(f"Timeout: {client.request_timeout}")
```

## Configuration Methods

### `get_api_token() -> str` (Class Method)

Retrieves the API token from Django settings.

**Returns**: API token string
**Settings Required**: `PAGBANK_API_TOKEN`

**Example**:
```python
token = PagBankClient.get_api_token()
```

### `get_api_url() -> str` (Class Method)

Retrieves the API base URL from Django settings.

**Returns**: API base URL string
**Settings Required**: `PAGBANK_API_URL`

**Example**:
```python
url = PagBankClient.get_api_url()
```

### `get_webhook_key() -> str` (Class Method)

Retrieves the webhook authentication key from Django settings.

**Returns**: Webhook key string
**Settings Required**: `PAGBANK_WEBHOOK_API_KEYS`

**Example**:
```python
webhook_key = PagBankClient.get_webhook_key()
```

## Public Key Management

### `create_public_key() -> requests.Response`

Creates a new public key for card encryption.

**HTTP Method**: POST
**Endpoint**: `/public-keys`
**Payload**: `{"type": "card"}`

**Returns**: `requests.Response` object
**Raises**: `PaymentGatewayClientRequestFailedError` on failure

**Example**:
```python
client = PagBankClient()
try:
    response = client.create_public_key()
    data = response.json()
    print(f"Public Key: {data['public_key']}")
    print(f"Created At: {data['created_at']}")
except PaymentGatewayClientRequestFailedError as e:
    print(f"Failed to create public key: {e}")
```

### `change_public_key() -> requests.Response`

Changes the current public key (used when key exists but is expired).

**HTTP Method**: PUT
**Endpoint**: `/public-keys/card`

**Returns**: `requests.Response` object
**Raises**: `PaymentGatewayClientRequestFailedError` on failure

**Example**:
```python
client = PagBankClient()
try:
    response = client.change_public_key()
    data = response.json()
    print(f"New Public Key: {data['public_key']}")
except PaymentGatewayClientRequestFailedError as e:
    print(f"Failed to change public key: {e}")
```

### `get_existing_public_key_from_db() -> PagBankPublicKey`

Retrieves the most recent valid public key from the database.

**Returns**: `PagBankPublicKey` instance or `None`

**Example**:
```python
client = PagBankClient()
existing_key = client.get_existing_public_key_from_db()
if existing_key:
    print(f"Using existing key: {existing_key.key[:20]}...")
else:
    print("No valid key found in database")
```

### `get_public_key() -> str`

Main method to retrieve a public key. Handles the complete flow:
1. Check for existing valid key in database
2. Create new key if none exists
3. Handle expired key replacement
4. Store key in database

**Returns**: Public key string
**Raises**: `PaymentGatewayClientRequestFailedError` on failure

**Example**:
```python
client = PagBankClient()
try:
    public_key = client.get_public_key()
    print(f"Public Key: {public_key}")
except PaymentGatewayClientRequestFailedError as e:
    print(f"Failed to get public key: {e}")
```

## Order Processing

### `create_credit_card_order(order: Order) -> requests.Response`

Creates a credit card payment order.

**HTTP Method**: POST
**Endpoint**: `/orders`

**Parameters**:
- `order`: Order instance with complete payment information

**Returns**: `requests.Response` object
**Side Effects**:
- Updates order with external_id
- Updates charge with status and external_id
- Updates related trip contract charge status
- Raises HTTP error on failure

**Example**:
```python
from payments.orders.models import Order

client = PagBankClient()
order = Order.objects.get(reference_id="order_123")

try:
    response = client.create_credit_card_order(order)
    print(f"Order created successfully: {response.status_code}")
    
    # Order is automatically updated with external_id
    order.refresh_from_db()
    print(f"External ID: {order.external_id}")
    
except requests.HTTPError as e:
    print(f"HTTP Error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### `create_pix_order(order: Order) -> requests.Response`

Creates a PIX payment order with QR code generation.

**HTTP Method**: POST
**Endpoint**: `/orders`

**Parameters**:
- `order`: Order instance with PIX payment details

**Returns**: `requests.Response` object
**Side Effects**:
- Updates order with external_id
- Updates QR code with text and image links
- Raises HTTP error on failure

**Example**:
```python
from payments.orders.models import Order, OrderQRCode

client = PagBankClient()
order = Order.objects.get(reference_id="pix_order_123")

try:
    response = client.create_pix_order(order)
    print(f"PIX order created successfully: {response.status_code}")
    
    # QR code is automatically updated
    qr_code = order.qr_codes.first()
    print(f"QR Code Text: {qr_code.text}")
    print(f"PNG Link: {qr_code.png_link}")
    print(f"Base64 Link: {qr_code.base64_link}")
    
except requests.HTTPError as e:
    print(f"HTTP Error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### `update_pix_order(request: Request, order: Order, data: dict) -> DRFResponse`

Updates PIX order status based on webhook data.

**Parameters**:
- `request`: Django REST Framework request object
- `order`: Order instance to update
- `data`: Webhook payload dictionary

**Returns**: `DRFResponse` object
**Side Effects**:
- Validates webhook data using serializer
- Updates charge status and payment information
- Links payment charge to trip contract charge
- Sends email notification
- Logs request and response

**Example**:
```python
from rest_framework.request import Request
from payments.orders.models import Order

# This method is typically called from webhook view
webhook_data = {
    "reference_id": "order_123",
    "charges": [{
        "id": "CHAR_123456789",
        "status": "PAID",
        "paid_at": "2024-01-15T10:30:00Z",
        "amount": {"value": 10000, "currency": "BRL"},
        "payment_method": {
            "type": "PIX",
            "pix": {
                "holder": {"name": "João Silva", "document": "12345678901"}
            }
        }
    }]
}

client = PagBankClient()
order = Order.objects.get(external_id="ORDER_123")

response = client.update_pix_order(request, order, webhook_data)
print(f"Update response: {response.status_code}")
```

## Payment Management

### `cancel_payment(charge: OrderCharge, company: Company) -> requests.Response`

Cancels an existing payment charge.

**HTTP Method**: POST
**Endpoint**: `/charges/{charge_id}/cancel`

**Parameters**:
- `charge`: OrderCharge instance to cancel
- `company`: Company instance for email notifications

**Returns**: `requests.Response` object or `None` if cancellation fails
**Side Effects**:
- Updates charge status to CANCELED
- Sets cancel_status to CANCELED
- Updates canceled_at timestamp
- Updates related trip contract charge status
- Sends email notification
- Logs cancellation attempt

**Example**:
```python
from payments.orders.models import OrderCharge
from companies.models import Company

client = PagBankClient()
charge = OrderCharge.objects.get(external_id="CHAR_123456789")
company = Company.objects.get(id=1)

try:
    response = client.cancel_payment(charge, company)
    
    if response:
        print(f"Payment canceled successfully: {response.status_code}")
        charge.refresh_from_db()
        print(f"Charge status: {charge.status}")
        print(f"Cancel status: {charge.cancel_status}")
        print(f"Canceled at: {charge.canceled_at}")
    else:
        print("Payment cancellation failed")
        charge.refresh_from_db()
        print(f"Cancel status: {charge.cancel_status}")
        
except Exception as e:
    print(f"Error during cancellation: {e}")
```

## Internal Helper Methods

### `_get_headers() -> dict`

Constructs HTTP headers for API requests.

**Returns**: Dictionary with headers
- `accept`: "*/*"
- `Authorization`: "Bearer {api_token}"
- `content-type`: "application/json"

**Example**:
```python
client = PagBankClient()
headers = client._get_headers()
print(headers)
# Output: {
#     "accept": "*/*",
#     "Authorization": "Bearer your_token_here",
#     "content-type": "application/json"
# }
```

## Status Mappings

The client uses predefined mappings to convert between PagBank and internal statuses:

### Payment Status Mapping

```python
PAYMENT_STATUS_MAPPING = {
    ChargePaymentStatus.IN_ANALYSIS: OrderCharge.Status.PROCESSING,
    ChargePaymentStatus.CANCELED: OrderCharge.Status.CANCELED,
    ChargePaymentStatus.DECLINED: OrderCharge.Status.DECLINED,
    ChargePaymentStatus.AUTHORIZED: OrderCharge.Status.AUTHORIZED,
    ChargePaymentStatus.PAID: OrderCharge.Status.PAID,
    ChargePaymentStatus.WAITING: OrderCharge.Status.PENDING,
}
```

### Trip Charge Status Mapping

```python
TRIP_CHARGE_STATUS_MAPPING = {
    OrderCharge.Status.AUTHORIZED: TripContractCharge.Status.PENDING,
    OrderCharge.Status.CANCELED: TripContractCharge.Status.REFUNDED,
    OrderCharge.Status.CREATED: TripContractCharge.Status.PENDING,
    OrderCharge.Status.DECLINED: TripContractCharge.Status.PENDING,
    OrderCharge.Status.PAID: TripContractCharge.Status.PAID,
    OrderCharge.Status.FAILED: TripContractCharge.Status.PENDING,
    OrderCharge.Status.PROCESSING: TripContractCharge.Status.PENDING,
}
```

## Error Handling

All methods that make HTTP requests include comprehensive error handling:

1. **Request Exceptions**: Caught and wrapped in `PaymentGatewayClientRequestFailedError`
2. **HTTP Errors**: Automatically raised using `response.raise_for_status()`
3. **Logging**: All requests and responses are logged with sensitive data redacted
4. **Sentry Integration**: Exceptions are captured for monitoring

**Example Error Handling Pattern**:
```python
try:
    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    
    # Log response (with sensitive data redacted)
    log_from_requests_response(
        response,
        redacted_fields={"request_headers": [{"key": "Authorization"}]}
    )
    
    # Raise exception for HTTP errors
    response.raise_for_status()
    
    return response
    
except requests.exceptions.RequestException as error:
    # Capture exception for monitoring
    capture_exception(error)
    
    # Raise custom exception
    raise PaymentGatewayClientRequestFailedError(
        "Operation failed"
    ) from error
```

## Usage Best Practices

1. **Always handle exceptions** when calling client methods
2. **Check response status codes** before processing data
3. **Use database transactions** when updating multiple related objects
4. **Monitor logs** for API interaction debugging
5. **Test with sandbox environment** before production deployment
6. **Implement retry logic** for transient failures
7. **Cache public keys** to reduce API calls
8. **Validate order data** before sending to PagBank

## Thread Safety

The `PagBankClient` class is thread-safe for read operations. For write operations involving database updates, ensure proper transaction handling and consider using database-level locking if concurrent access is expected.

## Performance Considerations

- **Request Timeout**: Set to 30 seconds by default
- **Connection Pooling**: Consider using session objects for high-volume scenarios
- **Rate Limiting**: Be aware of PagBank's API rate limits
- **Caching**: Public keys are cached in the database to reduce API calls
- **Async Processing**: Webhook updates trigger async email tasks to avoid blocking