# ecommerce_azure

## API Endpoints

All API routes are prefixed with `/api/`.

### Users
- `POST /api/users/register/` Register a new user.
- `POST /api/users/token/` Obtain an auth token.
- `GET /api/users/me/` Get the authenticated user profile.

### Products
- `GET /api/products/` List active products.
- `GET /api/products/<id>/` Retrieve a product.

### Cart & Checkout
- `GET /api/cart/` Get the current cart.
- `POST /api/cart/items/` Add or update a cart item.
- `POST /api/checkout/` Submit the cart for checkout.

### Payments
- `POST /api/payments/paystack/initialize/` Start a Paystack payment for a pending order.
- `POST /api/payments/paystack/verify/` Verify a Paystack payment server-to-server and finalize the order on success.
- `POST /api/payments/paystack/webhook/` Receive Paystack webhook events (`charge.success`) and finalize the order on success.
- `POST /api/payments/mpesa/stk-push/` Start an M-Pesa STK push for a pending order.
- `POST /api/payments/mpesa/callback/` Receive the M-Pesa callback and finalize the order on success.

Payment provider is set automatically based on the endpoint used (Paystack or M-Pesa), so clients do not send a provider value in the request.

## Database Configuration

The app uses SQLite in development. Set `DEBUG=True` locally to keep SQLite. When `DEBUG` is `False` and PostgreSQL environment variables are provided, the app connects to PostgreSQL:

```
POSTGRES_DB=your_db_name
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
POSTGRES_HOST=your_db_host
POSTGRES_PORT=5432
```
