# PagBank Webhooks Documentation

## Overview

PagBank webhooks provide real-time notifications about payment status changes. This integration includes secure webhook authentication, data validation, and automatic order processing.

## Webhook Flow

```
PagBank → Webhook Request → Authentication → Validation → Processing → Response
```

1. **PagBank sends webhook**: Payment status changes trigger webhook calls
2. **Authentication**: Request signature is verified using HMAC
3. **Validation**: Payload is validated using serializers
4. **Processing**: Order and charge status are updated
5. **Response**: HTTP 204 (success) or error code returned

## Webhook Endpoint

### POST `/api/payments/integrations/pagbank/webhooks/orders/`

Receives payment status updates from PagBank.

**View Class**: `PagBankOrderWebHook`
**Authentication**: `PagBankTokenAuthentication` (production only)
**Permissions**: `AllowAny`

## Authentication

### PagBankTokenAuthentication

Custom authentication class that verifies webhook signatures.

```python
class PagBankTokenAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request: Request):
        # Extract token from headers
        token = request.headers.get("X-Authenticity-Token")
        
        # Generate expected signature
        expected_token = generate_signature(
            PagBankClient().get_api_token(),
            json.dumps(request.data, separators=(",", ":"))
        )
        
        # Verify signature
        if not token or (token != expected_token):
            raise AuthenticationFailed
            
        return (AnonymousUser, None)
```

### Signature Generation

The `generate_signature` function creates HMAC signatures for webhook verification.

```python
from payments.integrations.pagbank.webhooks.helpers import generate_signature

# Generate signature for verification
api_token = "your_api_token"
payload = '{"reference_id":"order_123","charges":[...]}'
signature = generate_signature(api_token, payload)
```

**Implementation Location**: `payments/integrations/pagbank/webhooks/helpers.py`

### Environment-Based Authentication

Authentication is only enforced in production:

```python
@property
def authentication_classes(self):
    if settings.ENVIRONMENT != SystemEnvironments.PRODUCTION:
        return []  # No authentication in non-production
    
    return [PagBankTokenAuthentication]
```

## Request Headers

### Required Headers

- `X-Product-Id`: Order external ID from PagBank
- `X-Authenticity-Token`: HMAC signature for authentication (production only)

### Example Headers

```http
POST /api/payments/integrations/pagbank/webhooks/orders/
Content-Type: application/json
X-Product-Id: ORDER_123456789
X-Authenticity-Token: sha256=abc123...
```

## Webhook Payload

### Structure

```json
{
    "reference_id": "order_reference_123",
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
                    "id": "PIX_123456789",
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

### Payment Statuses

| PagBank Status | Internal Status | Description |
|----------------|-----------------|-------------|
| `WAITING` | `PENDING` | Awaiting payment |
| `IN_ANALYSIS` | `PROCESSING` | Under analysis |
| `PAID` | `PAID` | Payment completed |
| `AUTHORIZED` | `AUTHORIZED` | Payment authorized |
| `DECLINED` | `DECLINED` | Payment declined |
| `CANCELED` | `CANCELED` | Payment canceled |

## Data Validation

### PagBankOrderWebhookSerializer

Main serializer for webhook payloads:

```python
class PagBankOrderWebhookSerializer(serializers.ModelSerializer):
    charges = PagBankChargeWebhookSerializer(many=True)

    class Meta:
        model = Order
        fields = ["reference_id", "charges"]
```

### PagBankChargeWebhookSerializer

Validates individual charge data:

```python
class PagBankChargeWebhookSerializer(serializers.ModelSerializer):
    payment_method = PagBankPaymentMethodSerializer()
    amount = serializers.SerializerMethodField()

    class Meta:
        model = OrderCharge
        fields = [
            "id", "order", "status", "paid_at", 
            "amount", "value", "currency", "payment_method"
        ]
```

### PagBankPixSerializer

Handles PIX payment method data:

```python
class PagBankPixSerializer(serializers.ModelSerializer):
    holder = PagBankPixHolderSerializer(write_only=True, required=False)

    class Meta:
        model = OrderChargePaymentMethodPIX
        fields = [
            "id", "payment_method", "holder", 
            "holder_name", "holder_document"
        ]
```

## Processing Logic

### Order Processing Flow

1. **Extract Order ID**: Get `X-Product-Id` from headers
2. **Fetch Order**: Retrieve order by external_id
3. **Validate Data**: Use serializers to validate payload
4. **Update Status**: Update charge and order status
5. **Link Relations**: Connect payment to trip contract charges
6. **Send Notifications**: Trigger email notifications
7. **Return Response**: Send HTTP 204 or error

### Database Updates

The webhook processing performs several database updates:

```python
@transaction.atomic
def update(self, instance, validated_data):
    charges_data = validated_data.pop("charges")
    
    # Create or update charges
    for charge_data in charges_data:
        charge_data["order"] = instance
    
    # Process charges using serializer
    PagBankChargeWebhookSerializer(
        data=charges_data, 
        many=True
    ).create(charges_data)
    
    return super().update(instance, validated_data)
```

### Trip Contract Integration

Webhooks automatically link payments to trip contract charges:

```python
if payment_method.type == OrderChargePaymentMethod.Types.PIX:
    if qr_code := instance.order.qr_codes.first():
        charge_relation = qr_code.to_trip_contract_charge.first()
        charge_relation.payment_charge = instance
        charge_relation.save(update_fields=["payment_charge"])
```

## Error Handling

### Validation Errors

```python
try:
    serializer.is_valid(raise_exception=True)
except ValidationError as err:
    response = DRFResponse(
        err.detail,
        status=status.HTTP_400_BAD_REQUEST,
    )
    
    log_from_request(request, response)
    return response
```

### Authentication Errors

```python
class PagBankTokenAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request: Request):
        # ... signature verification ...
        
        if not token or (token != expected_token):
            raise AuthenticationFailed  # Returns HTTP 401
```

### Processing Errors

Processing errors are logged but don't prevent webhook acknowledgment:

```python
with suppress(AttributeError), transaction.atomic():
    # Update trip contract charges
    # If this fails, webhook still returns 204
    pass
```

## Response Codes

| Code | Status | Description |
|------|--------|-------------|
| 204 | No Content | Webhook processed successfully |
| 400 | Bad Request | Invalid payload data |
| 401 | Unauthorized | Invalid signature |
| 404 | Not Found | Order not found |
| 500 | Server Error | Internal processing error |

## Logging

All webhook requests and responses are logged:

```python
log_from_request(request, response)
```

**Logged Information**:
- Request headers (with sensitive data redacted)
- Request payload
- Response status and data
- Processing timestamp
- Any errors encountered

## Testing Webhooks

### Unit Tests

```python
from django.test import TestCase
from payments.integrations.pagbank.webhooks.views import PagBankOrderWebHook

class WebhookTest(TestCase):
    def test_webhook_processing(self):
        # Create test order
        order = self.create_test_order()
        
        # Prepare webhook payload
        webhook_data = {
            "reference_id": str(order.reference_id),
            "charges": [{
                "id": "CHAR_123456789",
                "status": "PAID",
                "amount": {"value": 10000, "currency": "BRL"},
                "payment_method": {
                    "type": "PIX",
                    "pix": {"holder": {"name": "Test", "document": "123"}}
                }
            }]
        }
        
        # Send webhook request
        response = self.client.post(
            "/api/payments/integrations/pagbank/webhooks/orders/",
            data=webhook_data,
            content_type="application/json",
            HTTP_X_PRODUCT_ID=order.external_id
        )
        
        # Verify response
        self.assertEqual(response.status_code, 204)
        
        # Verify order was updated
        order.refresh_from_db()
        charge = order.charges.first()
        self.assertEqual(charge.status, "PAID")
```

### Integration Tests

```python
class WebhookIntegrationTest(TestCase):
    def test_signature_verification(self):
        from payments.integrations.pagbank.webhooks.helpers import generate_signature
        
        # Generate valid signature
        payload = '{"reference_id":"test"}'
        signature = generate_signature("test_token", payload)
        
        # Test with valid signature
        response = self.client.post(
            "/webhook/endpoint/",
            data=payload,
            content_type="application/json",
            HTTP_X_AUTHENTICITY_TOKEN=signature
        )
        
        # Should not return 401
        self.assertNotEqual(response.status_code, 401)
```

### Mock Webhook Testing

```python
from unittest.mock import patch

class MockWebhookTest(TestCase):
    @patch('payments.integrations.pagbank.client.PagBankClient.get_api_token')
    def test_webhook_authentication(self, mock_token):
        mock_token.return_value = "test_token"
        
        # Test webhook with mocked token
        # ... test implementation ...
```

## Webhook Helpers

### URL Generation

```python
from payments.integrations.pagbank.webhooks.helpers import get_orders_webhook_url

webhook_url = get_orders_webhook_url()
# Returns: "https://your-api.com/api/payments/integrations/pagbank/webhooks/orders/"
```

### Signature Verification

```python
from payments.integrations.pagbank.webhooks.helpers import generate_signature

def verify_webhook_signature(request):
    received_signature = request.headers.get("X-Authenticity-Token")
    payload = json.dumps(request.data, separators=(",", ":"))
    expected_signature = generate_signature(api_token, payload)
    
    return received_signature == expected_signature
```

## Security Considerations

### Signature Verification

1. **Always verify signatures** in production
2. **Use constant-time comparison** to prevent timing attacks
3. **Validate payload format** before processing
4. **Log authentication failures** for monitoring

### Data Validation

1. **Validate all input data** using serializers
2. **Sanitize sensitive information** in logs
3. **Use database transactions** for atomic updates
4. **Implement idempotency** for duplicate webhooks

### Rate Limiting

Consider implementing rate limiting for webhook endpoints:

```python
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='100/m')
def webhook_view(request):
    # Webhook processing logic
    pass
```

## Monitoring and Alerting

### Key Metrics to Monitor

1. **Webhook Success Rate**: Percentage of successfully processed webhooks
2. **Response Times**: Time taken to process webhook requests
3. **Authentication Failures**: Number of signature verification failures
4. **Validation Errors**: Frequency of payload validation errors
5. **Processing Errors**: Internal errors during webhook processing

### Recommended Alerts

1. **High Error Rate**: Alert if webhook error rate exceeds 5%
2. **Authentication Failures**: Alert on repeated signature failures
3. **Processing Delays**: Alert if webhook processing takes > 10 seconds
4. **Missing Webhooks**: Alert if expected webhooks don't arrive

### Logging Best Practices

```python
import logging

logger = logging.getLogger(__name__)

def process_webhook(request):
    logger.info(f"Webhook received for order: {order_id}")
    
    try:
        # Process webhook
        logger.info(f"Webhook processed successfully: {order_id}")
    except Exception as e:
        logger.error(f"Webhook processing failed: {order_id}, Error: {e}")
        raise
```

## Troubleshooting

### Common Issues

1. **Signature Mismatch**
   - Verify API token configuration
   - Check payload serialization format
   - Ensure headers are correctly set

2. **Order Not Found**
   - Verify order external_id mapping
   - Check database synchronization
   - Validate order creation process

3. **Validation Errors**
   - Review payload structure
   - Check required fields
   - Validate data types

4. **Processing Timeouts**
   - Optimize database queries
   - Use async processing for heavy operations
   - Implement proper error handling

### Debug Mode

For debugging webhooks in development:

```python
# In settings.py
if DEBUG:
    LOGGING = {
        'loggers': {
            'payments.integrations.pagbank.webhooks': {
                'level': 'DEBUG',
                'handlers': ['console'],
            }
        }
    }
```

### Manual Testing

```bash
# Test webhook endpoint manually
curl -X POST http://localhost:8000/api/payments/integrations/pagbank/webhooks/orders/ \
  -H "Content-Type: application/json" \
  -H "X-Product-Id: ORDER_123" \
  -H "X-Authenticity-Token: signature_here" \
  -d '{"reference_id":"test","charges":[...]}'
```

## Best Practices

1. **Implement idempotency** to handle duplicate webhooks
2. **Use database transactions** for atomic operations
3. **Validate signatures** in production environments
4. **Log all webhook interactions** for debugging
5. **Monitor webhook health** and set up alerts
6. **Handle errors gracefully** and return appropriate status codes
7. **Process webhooks quickly** to avoid timeouts
8. **Use async tasks** for heavy processing operations