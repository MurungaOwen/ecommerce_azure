# API Reference

All API routes are prefixed with `/api/`.

## Authentication

The API uses token or session authentication. For token auth, obtain a token and send it in the `Authorization` header:

```
Authorization: Token <token>
```

### Obtain token
- `POST /api/users/token/`

Request body:
```json
{ "username": "string", "password": "string" }
```

Response body:
```json
{ "token": "string" }
```

## Users

### Register
- `POST /api/users/register/`

Request body:
```json
{
  "username": "string",
  "email": "string",
  "first_name": "string",
  "last_name": "string",
  "password": "string"
}
```

### Current user
- `GET /api/users/me/` (auth required)

## Products

### List products
- `GET /api/products/`

### Retrieve product
- `GET /api/products/{id}/`

## Cart & Checkout

### Get cart
- `GET /api/cart/` (auth required)

### Add/update/remove cart item
- `POST /api/cart/items/` (auth required)

Request body:
```json
{ "product_id": 1, "quantity": 2 }
```

Set `quantity` to `0` to remove the item.

### Checkout
- `POST /api/checkout/` (auth required)

Moves the cart to `payment_pending` and returns the order.

## Payments

### Paystack initialize
- `POST /api/payments/paystack/initialize/` (auth required)

Request body:
```json
{ "order_id": 1 }
```

Response body:
```json
{
  "order_id": 1,
  "reference": "paystack_xxx",
  "amount": "100.00",
  "currency": "KES",
  "authorization_url": "https://checkout.paystack.com/..."
}
```

### Paystack verify
- `POST /api/payments/paystack/verify/` (auth required)

Request body:
```json
{ "reference": "paystack_xxx", "status": "success" }
```

`status` defaults to `"success"` if omitted. A successful verification finalizes the order.

## Analytics

### App analytics overview
- `GET /api/analytics/overview/` (auth required)
- `GET /api/analytics/checkout/` (auth required; alias of overview)

Response body includes checkout summary plus user, product, and order metrics:
```json
{
  "summary": {
    "total_checkouts": 1,
    "total_revenue": "16.00",
    "total_items": 2
  },
  "recent_checkouts": [],
  "users": {
    "total_users": 10,
    "active_users": 9
  },
  "products": {
    "total_products": 12,
    "active_products": 10,
    "out_of_stock": 2
  },
  "orders": {
    "total_orders": 15,
    "status": {
      "cart": 2,
      "payment_pending": 1,
      "submitted": 12
    },
    "payment_status": {
      "pending": 1,
      "paid": 12,
      "failed": 2
    },
    "fulfillment_status": {
      "pending": 5,
      "processing": 3,
      "completed": 4,
      "cancelled": 3
    }
  }
}
```
