# PagBank Credit Card Payment Method Flow

## Overview

This document provides a detailed flowchart specifically for the credit card payment method processing in the PagBank integration, focusing on card encryption, tokenization, validation, and payment method handling.

## Credit Card Payment Method Flow

```mermaid
flowchart TD
    A[User Opens Payment Form] --> B[Frontend Requests Public Key]
    B --> C[GET /api/payments/integrations/pagbank/public-keys/]
    C --> D[PagBankPublicKeysView.get]
    
    D --> E[PagBankClient.get_public_key]
    E --> F{Valid Key in DB?}
    
    F -->|No| G[PagBankClient.create_public_key]
    F -->|Yes| H[Return Existing Key]
    
    G --> I[POST /public-keys to PagBank]
    I --> J[PagBankPublicKeyManager.create_from_api_response_data]
    J --> K[Store Key in Database]
    K --> L[Return Public Key]
    H --> L
    
    L --> M[PagBankPublicKeySerializer]
    M --> N[Frontend Receives Public Key]
    
    N --> O[User Enters Card Details]
    O --> P[Card Number: 4111111111111111]
    P --> Q[Expiry Date: 12/25]
    Q --> R[CVV: 123]
    R --> S[Holder Name: JOAO SILVA]
    S --> T[Holder Document: 12345678901]
    
    T --> U[Frontend Validates Card Format]
    U --> V{Card Valid?}
    
    V -->|No| W[Show Validation Error]
    W --> O
    
    V -->|Yes| X[Encrypt Card Data with Public Key]
    X --> Y[Generate Encrypted Token]
    Y --> Z[Create Payment Request]
    
    Z --> AA[POST Payment Request to Backend]
    AA --> BB[Backend Payment View/API]
    BB --> CC[Create OrderChargePaymentMethod]
    
    CC --> DD[OrderChargePaymentMethod.objects.create]
    DD --> EE[Set type = 'CREDIT_CARD']
    EE --> FF[Set installments count]
    FF --> GG[Link to OrderCharge]
    
    GG --> HH[Create OrderChargePaymentMethodCard]
    HH --> II[OrderChargePaymentMethodCard.objects.create]
    II --> JJ[Store card_token from frontend]
    JJ --> KK[Set payment_method relationship]
    
    KK --> LL[PagBankClient.create_credit_card_order]
    LL --> MM[PagBankOrderSerializer initialization]
    MM --> NN[PagBankChargeSerializer]
    NN --> OO[PagBankChargeCreditCardPaymentMethodSerializer]
    
    OO --> PP[Serialize Payment Method Data]
    PP --> QQ{Has Card Token?}
    
    QQ -->|No| RR[Validation Error]
    RR --> SS[Return 400 Bad Request]
    
    QQ -->|Yes| TT[Build Card Object]
    TT --> UU[card: encrypted: card_token]
    UU --> VV[type: CREDIT_CARD]
    VV --> WW[installments: count]
    WW --> XX[capture: true]
    
    XX --> YY[Send to PagBank API]
    YY --> ZZ[POST /orders with card data]
    ZZ --> AAA{PagBank Response?}
    
    AAA -->|Error| BBB[Handle API Error]
    BBB --> CCC[PaymentGatewayClientRequestFailedError]
    CCC --> DDD[Log Error Details]
    DDD --> EEE[Return Error to Frontend]
    
    AAA -->|Success| FFF[PagBankOrderCreditCardPaymentResponseSerializer]
    FFF --> GGG[Extract Response Data]
    GGG --> HHH[Update Order.external_id]
    HHH --> III[Update OrderCharge.external_id]
    III --> JJJ[Update OrderCharge.status]
    JJJ --> KKK[Update OrderCharge.paid_at]
    
    KKK --> LLL[PagBankCardDataCreditCardPaymentResponseSerializer]
    LLL --> MMM[Process Card Response Data]
    MMM --> NNN[Extract Card Information]
    
    NNN --> OOO[Update Card.brand]
    OOO --> PPP[Update Card.first_digits]
    PPP --> QQQ[Update Card.last_digits]
    QQQ --> RRR[Update Card.exp_month]
    RRR --> SSS[Update Card.exp_year]
    SSS --> TTT[Update Card.holder_name]
    TTT --> UUU[Update Card.holder_document]
    
    UUU --> VVV[Clear Sensitive Data]
    VVV --> WWW[card_token remains encrypted]
    WWW --> XXX[Save Card Model]
    
    XXX --> YYY[Update Trip Contract Charge]
    YYY --> ZZZ[Set status = PAID]
    ZZZ --> AAAA[Set paid_at timestamp]
    
    AAAA --> BBBB[Return Success Response]
    BBBB --> CCCC[Frontend Shows Success]
    
    CCCC --> DDDD[PagBank Webhook Triggered]
    DDDD --> EEEE[Webhook Updates Card Status]
    EEEE --> FFFF[Payment Method Complete]
```

## Card Data Processing Flow

```mermaid
flowchart TD
    A[Raw Card Data] --> B[Frontend Validation]
    B --> C{Card Number Valid?}
    C -->|No| D[Show Card Number Error]
    C -->|Yes| E{Expiry Date Valid?}
    E -->|No| F[Show Expiry Error]
    E -->|Yes| G{CVV Valid?}
    G -->|No| H[Show CVV Error]
    G -->|Yes| I{Holder Name Valid?}
    I -->|No| J[Show Name Error]
    I -->|Yes| K[Encrypt with Public Key]
    
    K --> L[RSA Encryption]
    L --> M[Base64 Encoding]
    M --> N[Generate Card Token]
    N --> O[Send to Backend]
    
    O --> P[OrderChargePaymentMethodCard]
    P --> Q[Store Encrypted Token]
    Q --> R[Link to Payment Method]
    R --> S[Send to PagBank]
    
    S --> T[PagBank Processes Card]
    T --> U[Returns Card Info]
    U --> V[Update Local Card Data]
    V --> W[Clear Sensitive Fields]
```

## Payment Method Serialization Flow

```mermaid
flowchart TD
    A[OrderChargePaymentMethod] --> B[PagBankChargeCreditCardPaymentMethodSerializer]
    B --> C[get_type method]
    C --> D[Returns 'CREDIT_CARD']
    
    B --> E[get_capture method]
    E --> F[Returns True]
    
    B --> G[get_card method]
    G --> H[Access payment_method.card]
    H --> I[Extract card_token]
    I --> J[Return encrypted token]
    
    B --> K[installments field]
    K --> L[Get installment count]
    
    D --> M[Combine Data]
    F --> M
    J --> M
    L --> M
    
    M --> N[Final Payload]
    N --> O[type: CREDIT_CARD]
    O --> P[capture: true]
    P --> Q[installments: 1-12]
    Q --> R[card: encrypted: token]
```

## Card Response Processing Flow

```mermaid
flowchart TD
    A[PagBank API Response] --> B[Extract payment_method]
    B --> C[Extract card data]
    C --> D[PagBankCardDataCreditCardPaymentResponseSerializer]
    
    D --> E[Process holder data]
    E --> F{Has holder object?}
    F -->|Yes| G[Extract holder.name]
    G --> H[Extract holder.document]
    H --> I[Set holder_name]
    I --> J[Set holder_document]
    F -->|No| K[Use existing holder data]
    
    J --> L[Update Card Fields]
    K --> L
    L --> M[brand: visa/mastercard/etc]
    M --> N[first_digits: 411111]
    N --> O[last_digits: 1111]
    O --> P[exp_month: 12]
    P --> Q[exp_year: 2025]
    Q --> R[holder_name: JOAO SILVA]
    R --> S[holder_document: 12345678901]
    
    S --> T[Save Card Model]
    T --> U[Card Data Updated]
```

## Card Validation Flow

```mermaid
flowchart TD
    A[Card Input] --> B{Card Number Length}
    B -->|< 13 digits| C[Invalid: Too Short]
    B -->|> 19 digits| D[Invalid: Too Long]
    B -->|13-19 digits| E[Luhn Algorithm Check]
    
    E --> F{Luhn Valid?}
    F -->|No| G[Invalid: Failed Checksum]
    F -->|Yes| H[Detect Card Brand]
    
    H --> I{Brand Detection}
    I -->|4xxx| J[Visa]
    I -->|5xxx| K[Mastercard]
    I -->|3xxx| L[American Express]
    I -->|6xxx| M[Discover]
    I -->|Other| N[Unknown Brand]
    
    J --> O[Check Expiry Date]
    K --> O
    L --> O
    M --> O
    N --> O
    
    O --> P{Expiry Format MM/YY?}
    P -->|No| Q[Invalid: Wrong Format]
    P -->|Yes| R{Future Date?}
    R -->|No| S[Invalid: Expired]
    R -->|Yes| T[Check CVV]
    
    T --> U{CVV Length}
    U -->|3-4 digits| V[Valid CVV]
    U -->|Other| W[Invalid: Wrong CVV]
    
    V --> X[Card Validation Complete]
```

## Error Handling for Card Processing

```mermaid
flowchart TD
    A[Card Processing Error] --> B{Error Type}
    
    B -->|Validation Error| C[Card Data Invalid]
    B -->|Encryption Error| D[Public Key Issue]
    B -->|API Error| E[PagBank Rejection]
    B -->|Database Error| F[Storage Issue]
    
    C --> G[Return 400 Bad Request]
    G --> H[Show Field Errors]
    
    D --> I[Regenerate Public Key]
    I --> J[Retry Encryption]
    J --> K{Success?}
    K -->|No| L[Return 500 Error]
    K -->|Yes| M[Continue Processing]
    
    E --> N{API Error Code}
    N -->|40001| O[Invalid Card]
    N -->|40002| P[Insufficient Funds]
    N -->|40003| Q[Card Blocked]
    N -->|Other| R[Generic API Error]
    
    O --> S[Return Card Error]
    P --> T[Return Funds Error]
    Q --> U[Return Block Error]
    R --> V[Return Generic Error]
    
    F --> W[Log Database Error]
    W --> X[Return 500 Error]
```

## Card Security Flow

```mermaid
flowchart TD
    A[Sensitive Card Data] --> B[Frontend Processing]
    B --> C[Encrypt with Public Key]
    C --> D[Clear Raw Data from Memory]
    D --> E[Send Encrypted Token]
    
    E --> F[Backend Receives Token]
    F --> G[Store in OrderChargePaymentMethodCard]
    G --> H[Never Decrypt on Backend]
    H --> I[Send Token to PagBank]
    
    I --> J[PagBank Processes Card]
    J --> K[Returns Safe Card Info]
    K --> L[Store Safe Fields Only]
    
    L --> M[brand: visa]
    M --> N[first_digits: 411111]
    N --> O[last_digits: 1111]
    O --> P[exp_month: 12]
    P --> Q[exp_year: 2025]
    Q --> R[holder_name: JOAO SILVA]
    
    R --> S[Encrypted Token Remains]
    S --> T[Never Store Raw Card Data]
    T --> U[PCI Compliance Maintained]
```

## Key Components for Card Processing

### Models
```python
# OrderChargePaymentMethod
class OrderChargePaymentMethod(models.Model):
    charge = models.OneToOneField(OrderCharge)
    type = models.CharField(choices=Types.choices)  # "CREDIT_CARD"
    installments = models.IntegerField(default=1)

# OrderChargePaymentMethodCard  
class OrderChargePaymentMethodCard(models.Model):
    payment_method = models.OneToOneField(OrderChargePaymentMethod)
    card_token = models.CharField(max_length=1024)  # Encrypted
    brand = models.CharField(max_length=50)         # "visa"
    first_digits = models.CharField(max_length=6)   # "411111"
    last_digits = models.CharField(max_length=4)    # "1111"
    exp_month = models.CharField(max_length=2)      # "12"
    exp_year = models.CharField(max_length=4)       # "2025"
    holder_name = models.CharField(max_length=100)  # "JOAO SILVA"
    holder_document = models.CharField(max_length=14) # "12345678901"
```

### Serializers
```python
# Request Serialization
class PagBankChargeCreditCardPaymentMethodSerializer(serializers.ModelSerializer):
    def get_type(self, _) -> str:
        return "CREDIT_CARD"
    
    def get_capture(self, _) -> bool:
        return True
    
    def get_card(self, obj: OrderChargePaymentMethod) -> dict:
        return {"encrypted": obj.card.card_token}

# Response Deserialization
class PagBankCardDataCreditCardPaymentResponseSerializer(serializers.ModelSerializer):
    def save(self, **kwargs):
        # Extract holder data from response
        holder_data = self.initial_data.pop("holder", None)
        if holder_data:
            self.instance.holder_name = holder_data.get("name")
            self.instance.holder_document = holder_data.get("document")
        
        # Update other card fields
        for attr, value in self.validated_data.items():
            setattr(self.instance, attr, value)
        
        self.instance.save()
```

### Client Methods
```python
class PagBankClient:
    def create_credit_card_order(self, order: Order) -> requests.Response:
        # Serialize order with card data
        serializer = PagBankOrderSerializer(order)
        data = serializer.data
        
        # Send to PagBank API
        response = requests.post(url, headers=headers, json=data)
        
        # Process response and update card info
        response_serializer = PagBankOrderCreditCardPaymentResponseSerializer(
            order, data=response.json()
        )
        response_serializer.is_valid(raise_exception=True)
        response_serializer.save()
        
        return response
```

## Card Data Flow Summary

1. **Frontend**: User enters card details → Validates format → Encrypts with public key → Sends token
2. **Backend**: Creates payment method models → Stores encrypted token → Serializes for API
3. **PagBank**: Processes encrypted card → Returns safe card information
4. **Storage**: Updates card model with safe fields → Keeps token encrypted → Never stores raw data
5. **Webhooks**: Receives status updates → Updates payment status → Maintains security

This flow ensures PCI compliance by never storing raw card data while providing complete payment processing functionality through the PagBank integration.