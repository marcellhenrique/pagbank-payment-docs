# PagBank Payment Gateway Integration

A comprehensive Django-based integration with PagBank (formerly PagSeguro) payment gateway, supporting credit card payments, PIX transactions, webhooks, and marketplace revenue splitting.

## 🚀 Features

- ✅ **Credit Card Processing**: Secure tokenized payments with installments
- ✅ **PIX Payments**: Brazil's instant payment system with QR codes
- ✅ **Real-time Webhooks**: Automatic payment status updates
- ✅ **OAuth Integration**: Marketplace account authorization
- ✅ **Revenue Splitting**: Multi-party payment distribution
- ✅ **Public Key Management**: Automatic encryption key rotation
- ✅ **Comprehensive Logging**: Full audit trail and monitoring
- ✅ **Production Ready**: SSL, authentication, and error handling

## 📚 Documentation

### Core Documentation
- **[API Documentation](PAGBANK_API_DOCUMENTATION.md)** - Complete API reference with examples
- **[Setup Guide](docs/PAGBANK_SETUP_GUIDE.md)** - Installation and configuration instructions
- **[Client API Reference](docs/PAGBANK_CLIENT_API.md)** - Detailed client methods documentation
- **[Models Reference](docs/PAGBANK_MODELS_REFERENCE.md)** - Database models and relationships
- **[Webhooks Guide](docs/PAGBANK_WEBHOOKS.md)** - Webhook handling and authentication

### Payment Flow Documentation
- **[Complete Payment Flows](docs/PAGBANK_COMPLETE_PAYMENT_FLOWS.md)** - **🎯 Unified flowcharts for both payment methods**
- **[Credit Card Flow](docs/PAGBANK_CREDIT_CARD_FLOW.md)** - Credit card payment processing flowchart
- **[Credit Card Method Flow](docs/PAGBANK_CREDIT_CARD_METHOD_FLOW.md)** - Credit card method processing details
- **[PIX Payment Flow](docs/PAGBANK_PIX_PAYMENT_FLOW.md)** - PIX payment processing flowchart

### Quick Links
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [API Endpoints](#api-endpoints)
- [Testing](#testing)
- [Deployment](#deployment)

## 🛠 Installation

### Prerequisites
- Python 3.8+
- Django 3.2+
- PostgreSQL 12+
- Redis (for caching and async tasks)
- PagBank business account

### Quick Start

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure settings:**
```python
# settings.py
INSTALLED_APPS = [
    'payments.integrations.pagbank',
    'payments.integrations.pagbank.webhooks',
    # ... other apps
]

# PagBank configuration
PAGBANK_API_TOKEN = os.getenv('PAGBANK_API_TOKEN')
PAGBANK_API_URL = "https://api.pagbank.com"  # or sandbox URL
PAGBANK_WEBHOOK_API_KEYS = os.getenv('PAGBANK_WEBHOOK_API_KEYS')
```

3. **Run migrations:**
```bash
python manage.py migrate
```

4. **Set up webhooks:**
Configure webhook URL in PagBank dashboard:
```
https://yourdomain.com/api/payments/integrations/pagbank/webhooks/orders/
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# PagBank API Configuration
PAGBANK_API_TOKEN=your_api_token_here
PAGBANK_WEBHOOK_API_KEYS=your_webhook_key_here

# Environment (development/production)
ENVIRONMENT=development
PAGBANK_API_URL=https://sandbox.api.pagbank.com  # sandbox for dev

# OAuth (optional, for marketplace)
PAGBANK_APP_CLIENT_ID=your_client_id
PAGBANK_APP_CLIENT_SECRET=your_client_secret

# Application URLs
FRONT_END_URL=https://yourapp.com
API_URL=https://api.yourapp.com
```

## 🎯 Usage Examples

### Creating a Credit Card Payment

```python
from payments.integrations.pagbank.client import PagBankClient
from payments.orders.models import Order, Customer, OrderCharge

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

# Process payment
client = PagBankClient()
response = client.create_credit_card_order(order)
```

### Creating a PIX Payment

```python
from payments.orders.models import OrderQRCode

# Create QR code
qr_code = OrderQRCode.objects.create(
    order=order,
    amount=10000,
    expiration=timezone.now() + timedelta(hours=1)
)

# Generate PIX payment
response = client.create_pix_order(order)
```

## 🔗 API Endpoints

### Public Key Management
- `GET /api/payments/integrations/pagbank/public-keys/` - Get public key for encryption

### OAuth Authorization
- `POST /api/payments/integrations/pagbank/request-authorization/` - Start OAuth flow
- `GET /api/payments/integrations/pagbank/confirm-authorization/` - Handle OAuth callback
- `POST /api/payments/integrations/pagbank/disconnect-account/` - Disconnect account

### Webhooks
- `POST /api/payments/integrations/pagbank/webhooks/orders/` - Receive payment updates

## 🧪 Testing

```bash
# Run all tests
python manage.py test payments.integrations.pagbank

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

## 🚀 Deployment

### Production Checklist

- [ ] SSL certificate configured
- [ ] Production PagBank credentials
- [ ] Webhook URL registered with PagBank
- [ ] Environment variables set
- [ ] Database migrations applied
- [ ] Celery workers running
- [ ] Monitoring and logging configured

## 📊 Payment Flow Overview

### Credit Card vs PIX

| Aspect | Credit Card | PIX |
|--------|-------------|-----|
| **User Input** | Card details form | QR scan or copy-paste |
| **Security** | RSA encryption | Banking authentication |
| **Processing** | Synchronous | Asynchronous |
| **Completion** | Immediate or webhook | Always webhook |
| **User Experience** | Form submission | External banking app |

## 📋 Architecture

### Key Components

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

## 🆘 Troubleshooting

### Common Issues

**API Authentication Errors:**
```bash
# Verify API token
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://sandbox.api.pagbank.com/public-keys
```

**Webhook Signature Failures:**
- Check webhook key configuration
- Verify payload serialization format
- Ensure HTTPS is used in production

**Database Connection Issues:**
- Verify database credentials
- Check network connectivity
- Run migration status: `python manage.py showmigrations`

### Support Resources

- **PagBank Documentation**: https://developer.pagbank.com.br/
- **Integration Issues**: Check logs and error messages
- **Webhook Testing**: Use ngrok for local development
- **API Testing**: Use PagBank sandbox environment

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For technical support and questions:

1. **Check Documentation**: Review the comprehensive docs in this repository
2. **Search Issues**: Look for similar problems in project issues
3. **PagBank Support**: Contact PagBank through your business account
4. **Team Contact**: Reach out to the development team

---

## 📋 Project Status

- ✅ **Core Features**: Complete and tested
- ✅ **Production Ready**: Deployed and stable
- ✅ **Documentation**: Comprehensive guides available
- 🔄 **Maintenance**: Regular updates and improvements
- 📈 **Roadmap**: New features planned based on feedback

---

*Made with ❤️ for seamless payment processing in Brazil*