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

## Database Configuration

The app uses SQLite in development. When `DEBUG` is `False`, configure PostgreSQL with:

```
POSTGRES_DB=your_db_name
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
POSTGRES_HOST=your_db_host
POSTGRES_PORT=5432
```
