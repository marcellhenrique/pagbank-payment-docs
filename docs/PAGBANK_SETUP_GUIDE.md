# PagBank Integration Setup Guide

## Overview

This guide provides step-by-step instructions for setting up and configuring the PagBank payment gateway integration in your Django project.

## Prerequisites

### System Requirements

- Python 3.8+
- Django 3.2+
- PostgreSQL 12+ (recommended)
- Redis (for caching and Celery tasks)
- SSL certificate (required for production webhooks)

### PagBank Account Requirements

1. **PagBank Account**: Active PagBank business account
2. **API Credentials**: API token and webhook keys
3. **OAuth App**: Registered application for marketplace features (optional)

## Installation

### 1. Install Dependencies

Add the following to your `requirements.txt`:

```txt
# Core dependencies
Django>=3.2,<5.0
djangorestframework>=3.12.0
celery>=5.2.0
redis>=4.0.0
requests>=2.28.0
sentry-sdk>=1.9.0

# Date/time handling
python-dateutil>=2.8.0

# Authentication and permissions
django-cors-headers>=3.13.0

# API documentation (optional)
drf-yasg>=1.21.0
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 2. Django Settings Configuration

#### Basic Settings

Add to your `settings.py`:

```python
# settings.py

INSTALLED_APPS = [
    # ... your other apps ...
    'rest_framework',
    'payments',
    'payments.integrations.pagbank',
    'payments.integrations.pagbank.webhooks',
    'payments.orders',
    'companies',
]

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# Celery configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
```

#### PagBank Configuration

Add PagBank-specific settings:

```python
# PagBank API Configuration
PAGBANK_API_TOKEN = os.getenv('PAGBANK_API_TOKEN')
PAGBANK_WEBHOOK_API_KEYS = os.getenv('PAGBANK_WEBHOOK_API_KEYS')

# Environment-specific URLs
if os.getenv('ENVIRONMENT') == 'production':
    PAGBANK_API_URL = "https://api.pagbank.com"
    PAGBANK_CONNECT_BASE_URL = "https://connect.pagbank.com"
else:
    # Sandbox URLs for development/testing
    PAGBANK_API_URL = "https://sandbox.api.pagbank.com"
    PAGBANK_CONNECT_BASE_URL = "https://sandbox.connect.pagbank.com"

# OAuth Configuration (for marketplace features)
PAGBANK_APP_CLIENT_ID = os.getenv('PAGBANK_APP_CLIENT_ID')
PAGBANK_APP_CLIENT_SECRET = os.getenv('PAGBANK_APP_CLIENT_SECRET')

# Frontend URLs
FRONT_END_URL = os.getenv('FRONT_END_URL', 'http://localhost:3000')
API_URL = os.getenv('API_URL', 'http://localhost:8000')

# System environment
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
```

### 3. Environment Variables

Create a `.env` file in your project root:

```bash
# .env file

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/your_db

# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ENVIRONMENT=development

# PagBank Configuration
PAGBANK_API_TOKEN=your_pagbank_api_token_here
PAGBANK_WEBHOOK_API_KEYS=your_webhook_key_here

# OAuth (optional, for marketplace)
PAGBANK_APP_CLIENT_ID=your_client_id_here
PAGBANK_APP_CLIENT_SECRET=your_client_secret_here

# URLs
FRONT_END_URL=http://localhost:3000
API_URL=http://localhost:8000

# Redis
REDIS_URL=redis://localhost:6379/0

# Sentry (optional)
SENTRY_DSN=your_sentry_dsn_here
```

### 4. URL Configuration

Add PagBank URLs to your main `urls.py`:

```python
# urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/payments/', include('payments.urls')),
    # ... other URL patterns ...
]
```

Ensure the payments app includes PagBank URLs:

```python
# payments/urls.py
from django.urls import path, include

app_name = 'payments'

urlpatterns = [
    path('integrations/', include('payments.integrations.urls')),
    # ... other payment URLs ...
]
```

### 5. Database Migration

Run migrations to create the necessary database tables:

```bash
python manage.py makemigrations
python manage.py migrate
```

## Configuration

### 1. PagBank Account Setup

#### Get API Credentials

1. Log in to your PagBank account
2. Navigate to **Developer Tools** → **API Credentials**
3. Generate or copy your API token
4. Generate webhook authentication keys
5. Note your account ID for marketplace features

#### Configure Webhooks

1. In PagBank dashboard, go to **Webhooks**
2. Add webhook URL: `https://yourdomain.com/api/payments/integrations/pagbank/webhooks/orders/`
3. Select events: Payment status changes
4. Save webhook configuration

### 2. OAuth App Registration (Optional)

For marketplace features:

1. Go to **PagBank Connect** → **Applications**
2. Register new application
3. Set redirect URI: `https://yourdomain.com/api/payments/integrations/pagbank/confirm-authorization/`
4. Note Client ID and Client Secret
5. Configure required permissions:
   - `accounts.read`
   - `payments.refund`
   - `payments.split.read`

### 3. SSL Certificate Setup

Webhooks require HTTPS in production:

```bash
# Using Let's Encrypt with Certbot
sudo certbot --nginx -d yourdomain.com
```

### 4. Celery Setup

Start Celery worker for async tasks:

```bash
# Start Celery worker
celery -A your_project worker -l info

# Start Celery beat (for scheduled tasks)
celery -A your_project beat -l info
```

## Testing Setup

### 1. Unit Tests

Create test settings:

```python
# test_settings.py
from .settings import *

# Use in-memory database for tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable Celery for tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use sandbox URLs
PAGBANK_API_URL = "https://sandbox.api.pagbank.com"
PAGBANK_CONNECT_BASE_URL = "https://sandbox.connect.pagbank.com"

# Test credentials
PAGBANK_API_TOKEN = "test_token"
PAGBANK_WEBHOOK_API_KEYS = "test_webhook_key"
```

### 2. Test Data Setup

Create test fixtures:

```python
# tests/fixtures.py
import pytest
from django.utils import timezone
from payments.orders.models import Order, Customer, OrderCharge

@pytest.fixture
def test_customer():
    return Customer.objects.create(
        name="João Silva",
        email="joao@test.com",
        document="12345678901"
    )

@pytest.fixture
def test_order(test_customer):
    return Order.objects.create(
        customer=test_customer,
        payment_gateway="PAGBANK"
    )

@pytest.fixture
def test_charge(test_order):
    return OrderCharge.objects.create(
        order=test_order,
        reference_id="test_charge",
        description="Test payment",
        value=10000,
        currency="BRL"
    )
```

### 3. Run Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test payments.integrations.pagbank

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

## Development Workflow

### 1. Local Development

Start development services:

```bash
# Terminal 1: Django development server
python manage.py runserver

# Terminal 2: Celery worker
celery -A your_project worker -l info

# Terminal 3: Redis server
redis-server
```

### 2. Testing Payments

Use PagBank sandbox for testing:

```python
# Create test order
from payments.integrations.pagbank.client import PagBankClient
from payments.orders.models import Order

client = PagBankClient()
order = Order.objects.get(reference_id="test_order")

# Test credit card payment
response = client.create_credit_card_order(order)

# Test PIX payment
response = client.create_pix_order(order)
```

### 3. Webhook Testing

Use ngrok for local webhook testing:

```bash
# Install ngrok
npm install -g ngrok

# Expose local server
ngrok http 8000

# Use the HTTPS URL for webhook configuration
https://abc123.ngrok.io/api/payments/integrations/pagbank/webhooks/orders/
```

## Production Deployment

### 1. Environment Configuration

Production environment variables:

```bash
# Production .env
ENVIRONMENT=production
DEBUG=False
PAGBANK_API_URL=https://api.pagbank.com
PAGBANK_CONNECT_BASE_URL=https://connect.pagbank.com

# Use production credentials
PAGBANK_API_TOKEN=your_production_token
PAGBANK_WEBHOOK_API_KEYS=your_production_webhook_key

# Production URLs
FRONT_END_URL=https://yourapp.com
API_URL=https://api.yourapp.com
```

### 2. Security Settings

```python
# Production security settings
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# CORS settings
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "https://yourapp.com",
]

# Webhook authentication (always enabled in production)
ENVIRONMENT = 'production'
```

### 3. Database Configuration

```python
# Production database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}
```

### 4. Logging Configuration

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/pagbank.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'payments.integrations.pagbank': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### 5. Monitoring Setup

#### Sentry Integration

```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn=os.getenv('SENTRY_DSN'),
    integrations=[
        DjangoIntegration(auto_enabling=True),
        CeleryIntegration(monitor_beat_tasks=True),
    ],
    traces_sample_rate=0.1,
    send_default_pii=False,
    environment=os.getenv('ENVIRONMENT', 'development'),
)
```

#### Health Checks

```python
# health/views.py
from django.http import JsonResponse
from django.db import connections
from payments.integrations.pagbank.models import PagBankPublicKey

def health_check(request):
    try:
        # Check database
        connections['default'].cursor()
        
        # Check PagBank integration
        key = PagBankPublicKey.valid_objects.first()
        
        return JsonResponse({
            'status': 'healthy',
            'database': 'connected',
            'pagbank_keys': 'available' if key else 'none',
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=500)
```

## Troubleshooting

### Common Issues

#### 1. API Authentication Errors

```bash
# Check API token
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://sandbox.api.pagbank.com/public-keys

# Expected: 200 OK with public key data
```

#### 2. Webhook Signature Failures

```python
# Debug webhook authentication
import json
from payments.integrations.pagbank.webhooks.helpers import generate_signature

payload = '{"reference_id":"test"}'
expected_signature = generate_signature("your_webhook_key", payload)
print(f"Expected signature: {expected_signature}")
```

#### 3. Database Connection Issues

```bash
# Test database connection
python manage.py dbshell

# Run migrations
python manage.py migrate --check
```

#### 4. Celery Task Failures

```bash
# Check Celery worker status
celery -A your_project inspect active

# Monitor task queue
celery -A your_project monitor
```

### Debug Mode

Enable debug logging:

```python
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'payments.integrations.pagbank': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

### Performance Monitoring

Monitor key metrics:

1. **API Response Times**: Track PagBank API call duration
2. **Webhook Processing**: Monitor webhook processing time
3. **Database Queries**: Use Django Debug Toolbar
4. **Celery Tasks**: Monitor task execution time
5. **Error Rates**: Track payment failures and errors

## Maintenance

### Regular Tasks

#### 1. Public Key Rotation

Public keys expire after 6 months. Set up monitoring:

```python
# management/commands/check_public_keys.py
from django.core.management.base import BaseCommand
from payments.integrations.pagbank.models import PagBankPublicKey

class Command(BaseCommand):
    def handle(self, *args, **options):
        expiring_keys = PagBankPublicKey.objects.filter(
            expires_at__lte=timezone.now() + timedelta(days=30)
        )
        
        if expiring_keys.exists():
            self.stdout.write('Public keys expiring soon!')
```

#### 2. Database Cleanup

Clean up old records:

```python
# Cleanup expired public keys
PagBankPublicKey.objects.filter(expired=True).delete()

# Archive old orders (older than 2 years)
old_orders = Order.objects.filter(
    created__lte=timezone.now() - timedelta(days=730)
)
```

#### 3. Log Rotation

Set up log rotation:

```bash
# /etc/logrotate.d/django-pagbank
/var/log/django/pagbank.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
}
```

### Backup Strategy

#### Database Backups

```bash
# Daily database backup
pg_dump -h localhost -U user -d database > backup_$(date +%Y%m%d).sql

# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups/pagbank"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME > $BACKUP_DIR/backup_$DATE.sql
gzip $BACKUP_DIR/backup_$DATE.sql
```

#### Configuration Backups

```bash
# Backup environment configuration
cp .env .env.backup.$(date +%Y%m%d)

# Backup Django settings
git add settings/
git commit -m "Backup configuration $(date)"
```

## Support

### Documentation References

- [PagBank Developer Documentation](https://developer.pagbank.com.br/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Celery Documentation](https://docs.celeryproject.org/)

### Getting Help

1. **Check logs** for error details
2. **Review API documentation** for parameter requirements
3. **Test in sandbox** before production deployment
4. **Monitor webhook deliveries** in PagBank dashboard
5. **Use debug mode** for detailed error information

### Contact Information

- **PagBank Technical Support**: Available through your PagBank account
- **Integration Issues**: Check project documentation and team contacts
- **Emergency Support**: Follow your organization's escalation procedures

---

*Setup Guide Version: 1.0*
*Last Updated: 2024*