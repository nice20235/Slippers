# Restaurant API

A FastAPI-based restaurant management system with user authentication, food management, and order processing.

## Features

- **User Authentication**: JWT-based authentication with access and refresh tokens
- **User Management**: User registration, login, and role-based access control
- **Slipper Management**: CRUD operations for slipper items (admin only)
- **Order Management**: Create, view, update, and delete orders
- **Database**: Async SQLAlchemy with PostgreSQL or SQLite support

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Configuration**:
   Create a `.env` file in the root directory:
   ```env
   # Database Configuration
   DATABASE_URL=postgresql+asyncpg://user:password@localhost/restaurant
   
   # JWT Configuration
   SECRET_KEY=your-super-secret-key-here
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=15
   
   # Optional: For development with SQLite
   # DATABASE_URL=sqlite+aiosqlite:///./restaurant.db
   ```

3. **Database Setup**:
   - For PostgreSQL: Create a database named `restaurant`
   - For SQLite: The database file will be created automatically

4. **Run the application**:
   ```bash
   python -m uvicorn app.main:app --reload
   ```

## API Endpoints

### Authentication
- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and get access/refresh tokens
- `POST /auth/refresh` - Get new access token using refresh token
- `POST /auth/reset-password` - Reset user password
- `POST /auth/logout` - Logout (client-side token deletion)

### Users (Admin only)
- `GET /users/` - List all users
- `GET /users/{user_id}` - Get user details
- `DELETE /users/{user_id}` - Delete user

### Slippers (Admin only for create/update/delete)
- `GET /slippers/` - List all slipper items
- `POST /slippers/` - Create new slipper item
- `PUT /slippers/{slipper_id}` - Update slipper item
- `DELETE /slippers/{slipper_id}` - Delete slipper item

### Orders
- `GET /orders/` - List orders (user's own orders, admin sees all)
- `POST /orders/` - Create new order
- `PUT /orders/{order_id}` - Update order
- `DELETE /orders/{order_id}` - Delete order

## Usage Examples

### Register a new user
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "john_doe", "email": "john@example.com", "password": "password123"}'
```

### Login
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "john_doe", "password": "password123"}'
```

### Create food item (Admin only)
```bash
curl -X POST "http://localhost:8000/slippers/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Pizza Margherita", "description": "Classic Italian pizza", "price": 12.99}'
```

### Create order
```bash
curl -X POST "http://localhost:8000/orders/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"slipper_id": 1, "quantity": 2}'
```

## Token Management

- **Access Token**: Valid for 15 minutes (configurable)
- **Refresh Token**: Valid for 7 days
- Use the refresh token to get a new access token when it expires

## Database Models

- **User**: username, email, hashed_password, role, is_active, created_at
- **Slipper**: image, name, size, price, quantity, created_at
- **Order**: user_id, slipper_id, quantity, created_at

## Security Features

- Password hashing with bcrypt
- JWT-based authentication
- Role-based access control (user/admin)
- Token refresh mechanism
- Input validation with Pydantic 