-- Best-effort generated PostgreSQL schema from SQLite
-- Please review before applying to production

CREATE TABLE IF NOT EXISTS "cart_items" (
  "id" BIGINT NOT NULL,
  "cart_id" BIGINT NOT NULL,
  "slipper_id" BIGINT NOT NULL,
  "quantity" BIGINT NOT NULL,
  "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "carts" (
  "id" BIGINT NOT NULL,
  "user_id" BIGINT NOT NULL,
  "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "categories" (
  "id" BIGINT NOT NULL,
  "name" TEXT NOT NULL,
  "description" TEXT,
  "is_active" BOOLEAN NOT NULL,
  "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "order_items" (
  "id" BIGINT NOT NULL,
  "order_id" BIGINT NOT NULL,
  "slipper_id" BIGINT NOT NULL,
  "quantity" BIGINT NOT NULL,
  "unit_price" DOUBLE PRECISION NOT NULL,
  "total_price" DOUBLE PRECISION NOT NULL,
  "notes" TEXT,
  "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "orders" (
  "id" BIGINT NOT NULL,
  "order_id" TEXT NOT NULL,
  "user_id" BIGINT NOT NULL,
  "status" TEXT NOT NULL,
  "total_amount" DOUBLE PRECISION NOT NULL,
  "notes" TEXT,
  "transfer_id" TEXT,
  "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "payment_uuid" TEXT,
  "idempotency_key" TEXT, PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "payments" (
  "id" BIGINT NOT NULL,
  "order_id" BIGINT,
  "shop_transaction_id" TEXT NOT NULL,
  "octo_payment_uuid" TEXT,
  "amount" DOUBLE PRECISION NOT NULL,
  "currency" TEXT NOT NULL,
  "status" TEXT NOT NULL,
  "raw" TEXT,
  "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "refund_requests" (
  "id" BIGINT NOT NULL,
  "order_id" BIGINT NOT NULL,
  "payment_id" BIGINT,
  "user_id" BIGINT NOT NULL,
  "admin_id" BIGINT,
  "amount" DOUBLE PRECISION NOT NULL,
  "reason" TEXT,
  "admin_note" TEXT,
  "status" TEXT NOT NULL,
  "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "processed_at" TIMESTAMP, PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "refunds" (
  "id" BIGINT NOT NULL,
  "refund_id" TEXT NOT NULL,
  "payment_id" BIGINT NOT NULL,
  "order_id" BIGINT,
  "requested_by" BIGINT NOT NULL,
  "processed_by" BIGINT,
  "amount" DOUBLE PRECISION NOT NULL,
  "currency" TEXT NOT NULL DEFAULT 'UZS',
  "reason" TEXT,
  "admin_notes" TEXT,
  "status" TEXT NOT NULL DEFAULT 'requested',
  "octo_payment_uuid" TEXT,
  "octo_response" TEXT,
  "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "processed_at" TIMESTAMP,
  "completed_at" TIMESTAMP,
  "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "slipper_images" (
  "id" BIGINT NOT NULL,
  "slipper_id" BIGINT NOT NULL,
  "image_path" TEXT NOT NULL,
  "is_primary" BOOLEAN NOT NULL,
  "alt_text" TEXT,
  "order_index" BIGINT NOT NULL,
  "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "slippers" (
  "id" BIGINT NOT NULL,
  "name" TEXT NOT NULL,
  "image" TEXT NOT NULL,
  "size" TEXT NOT NULL,
  "price" DOUBLE PRECISION NOT NULL,
  "quantity" BIGINT NOT NULL,
  "category_id" BIGINT,
  "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY ("id")
);

CREATE TABLE IF NOT EXISTS "users" (
  "id" BIGINT NOT NULL,
  "name" TEXT NOT NULL,
  "surname" TEXT NOT NULL,
  "phone_number" TEXT NOT NULL,
  "password_hash" TEXT NOT NULL,
  "is_admin" BOOLEAN NOT NULL,
  "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY ("id")
);

