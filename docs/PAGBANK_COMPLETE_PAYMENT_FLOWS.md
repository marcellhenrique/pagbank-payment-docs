# PagBank Complete Payment Flows Documentation

## Overview

This document provides comprehensive flowcharts for both PIX and Credit Card payment processing in the PagBank integration, showing the complete journey from payment initiation to completion for both payment methods, including all classes, functions, views, and serializers involved.

## Unified Payment Flow Overview

```mermaid
flowchart TD
    A[User Initiates Payment] --> B{Payment Method?}
    B -->|Credit Card| C[Credit Card Flow]
    B -->|PIX| D[PIX Flow]
    
    C --> E[Get Public Key]
    C --> F[Encrypt Card Data]
    C --> G[Create Payment Method Upfront]
    C --> H[Send to PagBank API]
    C --> I[Process Response Immediately]
    C --> J[Update Card Information]
    C --> K[Complete Payment]
    
    D --> L[Create Order with QR Code]
    D --> M[Generate PIX QR Code]
    D --> N[Display QR to User]
    D --> O[User Pays via Banking App]
    D --> P[Webhook Creates Payment Method]
    D --> Q[Process PIX Response]
    D --> R[Complete Payment]
    
    K --> S[Send Confirmation Email]
    R --> S
    S --> T[Payment Flow Complete]
```

## Complete Credit Card Payment Flow

```mermaid
flowchart TD
    A[User Selects Credit Card] --> B[Frontend Requests Public Key]
    B --> C[PagBankPublicKeysView.get]
    C --> D[PagBankClient.get_public_key]
    D --> E{Valid Key Exists?}
    
    E -->|No| F[PagBankClient.create_public_key]
    E -->|Yes| G[Return Existing Key]
    F --> H[Store in PagBankPublicKey Model]
    G --> I[PagBankPublicKeySerializer]
    H --> I
    
    I --> J[Frontend Receives Key]
    J --> K[User Enters Card Details]
    K --> L[Frontend Validates Card]
    L --> M[Encrypt with Public Key]
    M --> N[Generate Card Token]
    
    N --> O[Create Payment Request]
    O --> P[Customer.objects.create]
    P --> Q[Phone.objects.create]
    Q --> R[Address.objects.create]
    R --> S[Order.objects.create]
    S --> T[OrderItem.objects.create]
    T --> U[OrderCharge.objects.create]
    U --> V[OrderChargePaymentMethod.objects.create]
    V --> W[OrderChargePaymentMethodCard.objects.create]
    W --> X[OrderSplit.objects.create if needed]
    
    X --> Y[PagBankClient.create_credit_card_order]
    Y --> Z[PagBankOrderSerializer]
    Z --> AA[PagBankChargeCreditCardPaymentMethodSerializer]
    AA --> BB[POST /orders to PagBank]
    BB --> CC{API Response?}
    
    CC -->|Success| DD[PagBankOrderCreditCardPaymentResponseSerializer]
    CC -->|Error| EE[PaymentGatewayClientRequestFailedError]
    
    DD --> FF[Update Order.external_id]
    FF --> GG[Update OrderCharge Status]
    GG --> HH[PagBankCardDataCreditCardPaymentResponseSerializer]
    HH --> II[Update Card Information]
    II --> JJ[Update Trip Contract Charge]
    JJ --> KK[Return Success Response]
    
    EE --> LL[Log Error]
    LL --> MM[Return Error Response]
    
    KK --> NN[Webhook Processing Optional]
    NN --> OO[Credit Card Payment Complete]
    MM --> PP[Payment Failed]
```

## Complete PIX Payment Flow

```mermaid
flowchart TD
    A[User Selects PIX Payment] --> B[Create Payment Request]
    B --> C[Customer.objects.create]
    C --> D[Phone.objects.create]
    D --> E[Address.objects.create]
    E --> F[Order.objects.create]
    F --> G[OrderItem.objects.create]
    
    G --> H[OrderQRCode.objects.create]
    H --> I[Set amount and expiration]
    I --> J[OrderSplit.objects.create if needed]
    
    J --> K[PagBankClient.create_pix_order]
    K --> L[PagBankPixOrderSerializer]
    L --> M[PagBankQRCodeSerializer]
    M --> N[get_notification_urls method]
    N --> O[Include Webhook URLs]
    
    O --> P[POST /orders to PagBank]
    P --> Q{API Response?}
    
    Q -->|Success| R[PagBankPixOrderResponseSerializer]
    Q -->|Error| S[PaymentGatewayClientRequestFailedError]
    
    R --> T[Extract QR Code Data]
    T --> U[Update OrderQRCode Model]
    U --> V[qr_code.external_id]
    V --> W[qr_code.text PIX Code]
    W --> X[qr_code.png_link]
    X --> Y[qr_code.base64_link]
    
    Y --> Z[Return QR Code to Frontend]
    Z --> AA[Display QR Code to User]
    AA --> BB[User Scans QR or Copies Code]
    BB --> CC[User Opens Banking App]
    CC --> DD[User Confirms Payment]
    DD --> EE[PIX System Processes Payment]
    
    EE --> FF[PagBank Receives Confirmation]
    FF --> GG[PagBank Triggers Webhook]
    GG --> HH[POST /webhooks/orders/]
    HH --> II[PagBankOrderWebHook.post]
    
    II --> JJ{Production Environment?}
    JJ -->|Yes| KK[PagBankTokenAuthentication]
    JJ -->|No| LL[Skip Authentication]
    
    KK --> MM{Signature Valid?}
    MM -->|No| NN[Return 401 Unauthorized]
    MM -->|Yes| OO[Process Webhook]
    LL --> OO
    
    OO --> PP[PagBankOrderWebhookSerializer]
    PP --> QQ[PagBankChargeWebhookSerializer]
    QQ --> RR[Create OrderCharge from Webhook]
    RR --> SS[PagBankPaymentMethodSerializer]
    SS --> TT[Create OrderChargePaymentMethod]
    TT --> UU[Set type = 'PIX']
    UU --> VV[PagBankPixSerializer]
    VV --> WW[Create OrderChargePaymentMethodPIX]
    WW --> XX[Set PIX holder information]
    
    XX --> YY[Link to Trip Contract Charge]
    YY --> ZZ[Update Trip Status]
    ZZ --> AAA[Send Email Notification]
    AAA --> BBB[Return 204 No Content]
    
    S --> CCC[Log Error]
    CCC --> DDD[Return Error Response]
    NN --> EEE[Log Auth Failure]
    
    BBB --> FFF[PIX Payment Complete]
    DDD --> GGG[Payment Failed]
    EEE --> GGG
```

## Payment Method Comparison Flow

```mermaid
flowchart TD
    A[Payment Initiated] --> B{Payment Method?}
    
    B -->|Credit Card| C[Credit Card Branch]
    B -->|PIX| D[PIX Branch]
    
    C --> E[Public Key Required]
    C --> F[Card Encryption Needed]
    C --> G[Payment Method Created Upfront]
    C --> H[Immediate API Processing]
    C --> I[Synchronous Response]
    C --> J[Optional Webhook]
    
    D --> K[No Encryption Needed]
    D --> L[QR Code Generation Required]
    D --> M[No Payment Method Initially]
    D --> N[User Payment External]
    D --> O[Webhook-Driven Processing]
    D --> P[Asynchronous Response]
    
    E --> Q[Security: RSA Encryption]
    K --> R[Security: Banking App Auth]
    
    F --> S[User Experience: Form Input]
    L --> T[User Experience: QR Scan/Copy]
    
    G --> U[Data: Card Token Stored]
    M --> V[Data: QR Code Stored]
    
    H --> W[Processing: Immediate]
    N --> X[Processing: User-Initiated]
    
    I --> Y[Response: Real-time]
    O --> Z[Response: Webhook-based]
    
    J --> AA[Completion: Direct or Webhook]
    P --> BB[Completion: Always Webhook]
    
    Q --> CC[Payment Processed]
    R --> CC
    S --> CC
    T --> CC
    U --> CC
    V --> CC
    W --> CC
    X --> CC
    Y --> CC
    Z --> CC
    AA --> CC
    BB --> CC
```

## Shared Components Flow

```mermaid
flowchart TD
    A[Both Payment Methods] --> B[Shared Components]
    
    B --> C[Customer Creation]
    C --> D[Customer.objects.create]
    D --> E[Phone.objects.create]
    E --> F[Address.objects.create]
    
    B --> G[Order Management]
    G --> H[Order.objects.create]
    H --> I[OrderItem.objects.create]
    I --> J[OrderSplit.objects.create]
    
    B --> K[PagBank Client]
    K --> L[PagBankClient.__init__]
    L --> M[Authentication Headers]
    M --> N[API Communication]
    
    B --> O[Webhook Processing]
    O --> P[PagBankOrderWebHook.post]
    P --> Q[Signature Validation]
    Q --> R[Order Status Updates]
    
    B --> S[Trip Integration]
    S --> T[TripContractCharge Updates]
    T --> U[Status Mapping]
    U --> V[Email Notifications]
    
    B --> W[Error Handling]
    W --> X[PaymentGatewayClientRequestFailedError]
    X --> Y[Logging and Monitoring]
    Y --> Z[Sentry Integration]
    
    F --> AA[Base Models Ready]
    J --> AA
    N --> BB[API Ready]
    R --> CC[Webhooks Ready]
    V --> DD[Integration Ready]
    Z --> EE[Monitoring Ready]
    
    AA --> FF[Payment Processing Can Begin]
    BB --> FF
    CC --> FF
    DD --> FF
    EE --> FF
```

## Serializer Comparison Flow

```mermaid
flowchart TD
    A[Serializer Usage] --> B{Payment Method?}
    
    B -->|Credit Card| C[Credit Card Serializers]
    B -->|PIX| D[PIX Serializers]
    B -->|Both| E[Shared Serializers]
    
    C --> F[PagBankChargeCreditCardPaymentMethodSerializer]
    F --> G[Encrypts card data]
    F --> H[Sets type = 'CREDIT_CARD']
    F --> I[Handles installments]
    
    C --> J[PagBankOrderCreditCardPaymentResponseSerializer]
    J --> K[Processes API response]
    J --> L[Updates order and charge]
    
    C --> M[PagBankCardDataCreditCardPaymentResponseSerializer]
    M --> N[Updates card information]
    M --> O[Handles holder data]
    
    D --> P[PagBankQRCodeSerializer]
    P --> Q[Serializes QR code data]
    P --> R[Includes revenue splits]
    
    D --> S[PagBankPixOrderSerializer]
    S --> T[Includes notification URLs]
    S --> U[Handles QR codes array]
    
    D --> V[PagBankPixOrderResponseSerializer]
    V --> W[Processes QR response]
    V --> X[Updates QR code model]
    
    D --> Y[PagBankPixSerializer]
    Y --> Z[Handles PIX holder data]
    Y --> AA[Processes webhook PIX info]
    
    E --> BB[PagBankOrderSerializer]
    BB --> CC[Customer serialization]
    BB --> DD[Items serialization]
    
    E --> EE[PagBankOrderCustomerSerializer]
    EE --> FF[Customer data formatting]
    
    E --> GG[PagBankOrderWebhookSerializer]
    GG --> HH[Webhook data validation]
    GG --> II[Charge processing]
    
    E --> JJ[PagBankSplitReceiverSerializer]
    JJ --> KK[Revenue split handling]
    
    G --> LL[Card-Specific Processing]
    Q --> MM[PIX-Specific Processing]
    CC --> NN[Shared Processing]
    
    LL --> OO[Payment Method Created]
    MM --> OO
    NN --> OO
```

## Database Transaction Comparison

```mermaid
flowchart TD
    A[Payment Processing] --> B{Payment Method?}
    
    B -->|Credit Card| C[Credit Card Transaction]
    B -->|PIX| D[PIX Transaction]
    
    C --> E[Start Transaction]
    E --> F[Create Customer Models]
    F --> G[Create Order Models]
    G --> H[Create Payment Method]
    H --> I[Create Card Model]
    I --> J[Call PagBank API]
    J --> K{API Success?}
    K -->|Yes| L[Update with Response]
    K -->|No| M[Rollback Transaction]
    L --> N[Commit Transaction]
    
    D --> O[Start Transaction]
    O --> P[Create Customer Models]
    P --> Q[Create Order Models]
    Q --> R[Create QR Code Model]
    R --> S[Call PagBank API]
    S --> T{API Success?}
    T -->|Yes| U[Update QR Code Data]
    T -->|No| V[Rollback Transaction]
    U --> W[Commit Transaction]
    
    W --> X[Wait for User Payment]
    X --> Y[Webhook Triggers]
    Y --> Z[Start Webhook Transaction]
    Z --> AA[Create Charge Model]
    AA --> BB[Create Payment Method]
    BB --> CC[Create PIX Model]
    CC --> DD[Link to Trip Contracts]
    DD --> EE[Commit Webhook Transaction]
    
    N --> FF[Payment Method Ready]
    EE --> FF
    M --> GG[Transaction Failed]
    V --> GG
```

## Error Handling Unified Flow

```mermaid
flowchart TD
    A[Error Occurs] --> B{Error Source?}
    
    B -->|API Error| C[PagBank API Issue]
    B -->|Validation Error| D[Data Validation Issue]
    B -->|Authentication Error| E[Security Issue]
    B -->|Database Error| F[Storage Issue]
    B -->|Webhook Error| G[Webhook Processing Issue]
    
    C --> H{Payment Method?}
    H -->|Credit Card| I[Card-Specific Errors]
    H -->|PIX| J[PIX-Specific Errors]
    
    I --> K[Invalid Card Data]
    I --> L[Card Declined]
    I --> M[Encryption Issues]
    
    J --> N[QR Code Generation Failed]
    J --> O[Expired QR Code]
    J --> P[PIX Transaction Failed]
    
    D --> Q[Field Validation Errors]
    Q --> R[Return 400 Bad Request]
    
    E --> S[Invalid Signatures]
    S --> T[Return 401 Unauthorized]
    
    F --> U[Database Connection Issues]
    U --> V[Return 500 Server Error]
    
    G --> W[Webhook Signature Invalid]
    G --> X[Webhook Data Invalid]
    W --> T
    X --> R
    
    K --> Y[Log Error Details]
    L --> Y
    M --> Y
    N --> Y
    O --> Y
    P --> Y
    
    Y --> Z[Capture Exception]
    Z --> AA[Send to Sentry]
    AA --> BB[Alert Development Team]
    
    R --> CC[User Notification]
    T --> DD[Log Security Issue]
    V --> EE[System Alert]
    
    CC --> FF[Error Handled]
    DD --> FF
    EE --> FF
    BB --> FF
```

## Status Mapping Unified Flow

```mermaid
flowchart LR
    A[PagBank Status] --> B{Payment Method?}
    
    B -->|Credit Card| C[Card Status Mapping]
    B -->|PIX| D[PIX Status Mapping]
    
    C --> E[AUTHORIZED → OrderCharge.AUTHORIZED]
    C --> F[PAID → OrderCharge.PAID]
    C --> G[DECLINED → OrderCharge.DECLINED]
    C --> H[CANCELED → OrderCharge.CANCELED]
    
    D --> I[WAITING → OrderCharge.PENDING]
    D --> J[PAID → OrderCharge.PAID]
    D --> K[CANCELED → OrderCharge.CANCELED]
    
    E --> L[TripContractCharge.PENDING]
    F --> M[TripContractCharge.PAID]
    G --> N[TripContractCharge.PENDING]
    H --> O[TripContractCharge.REFUNDED]
    
    I --> P[TripContractCharge.PENDING]
    J --> Q[TripContractCharge.PAID]
    K --> R[TripContractCharge.REFUNDED]
    
    L --> S[Email: Processing]
    M --> T[Email: Success]
    N --> U[Email: Failed]
    O --> V[Email: Canceled]
    P --> W[Email: Pending]
    Q --> X[Email: Success]
    R --> Y[Email: Canceled]
    
    S --> Z[Status Updated]
    T --> Z
    U --> Z
    V --> Z
    W --> Z
    X --> Z
    Y --> Z
```

## Key Differences Summary

### Credit Card vs PIX Payment Flow Differences

| Aspect | Credit Card | PIX |
|--------|-------------|-----|
| **Public Key** | Required for encryption | Not needed |
| **User Input** | Card details form | QR scan or copy-paste |
| **Payment Method Creation** | Before API call | After webhook |
| **API Response** | Immediate processing | QR code generation |
| **User Action** | Submit form | External banking app |
| **Real-time Processing** | Synchronous | Asynchronous |
| **Webhook Dependency** | Optional enhancement | Essential for completion |
| **Expiration** | None | QR code expires (1 hour) |
| **Security** | RSA encryption | Banking authentication |
| **Error Handling** | Immediate feedback | Delayed feedback |

### Shared Components

Both payment methods share:
- **Customer/Order Creation**: Same models and process
- **PagBank Client**: Same authentication and base methods
- **Webhook Infrastructure**: Same signature validation
- **Trip Integration**: Same status mapping and updates
- **Email Notifications**: Same notification system
- **Error Logging**: Same monitoring and alerting

### Models Usage

```python
# Shared Models (Both Methods)
Customer, Phone, Address, Order, OrderItem, OrderCharge, OrderSplit

# Credit Card Specific
OrderChargePaymentMethodCard
PagBankPublicKey

# PIX Specific  
OrderQRCode
OrderChargePaymentMethodPIX

# Conditional (Created by webhook for PIX, upfront for Card)
OrderChargePaymentMethod
```

### Serializers Usage

```python
# Shared Serializers
PagBankOrderSerializer
PagBankOrderCustomerSerializer
PagBankOrderItemSerializer
PagBankSplitReceiverSerializer
PagBankOrderWebhookSerializer

# Credit Card Specific
PagBankChargeCreditCardPaymentMethodSerializer
PagBankOrderCreditCardPaymentResponseSerializer
PagBankCardDataCreditCardPaymentResponseSerializer
PagBankPublicKeySerializer

# PIX Specific
PagBankQRCodeSerializer
PagBankPixOrderSerializer
PagBankPixOrderResponseSerializer
PagBankPixSerializer
```

This comprehensive documentation provides a complete understanding of both payment flows, their similarities, differences, and how they integrate into your overall payment processing system. The unified approach helps developers understand when to use shared components and when payment-method-specific logic is required.