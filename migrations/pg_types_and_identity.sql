-- Type refinements and identity/defaults for PostgreSQL runtime

-- Money-like fields to NUMERIC(12,2)
ALTER TABLE "orders" ALTER COLUMN "total_amount" TYPE NUMERIC(12,2) USING "total_amount"::numeric(12,2);
ALTER TABLE "payments" ALTER COLUMN "amount" TYPE NUMERIC(12,2) USING "amount"::numeric(12,2);
ALTER TABLE "refunds" ALTER COLUMN "amount" TYPE NUMERIC(12,2) USING "amount"::numeric(12,2);

-- Sequences and defaults for IDs (auto-increment behavior)
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'categories_id_seq') THEN
    CREATE SEQUENCE categories_id_seq OWNED BY "categories"."id";
  END IF;
END $$;
ALTER TABLE "categories" ALTER COLUMN "id" SET DEFAULT nextval('categories_id_seq');
DO $$
DECLARE v_max bigint;
BEGIN
  SELECT MAX("id") INTO v_max FROM "categories";
  IF v_max IS NULL OR v_max < 1 THEN
    PERFORM setval('categories_id_seq', 1, false);
  ELSE
    PERFORM setval('categories_id_seq', v_max, true);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'users_id_seq') THEN
    CREATE SEQUENCE users_id_seq OWNED BY "users"."id";
  END IF;
END $$;
ALTER TABLE "users" ALTER COLUMN "id" SET DEFAULT nextval('users_id_seq');
DO $$
DECLARE v_max bigint;
BEGIN
  SELECT MAX("id") INTO v_max FROM "users";
  IF v_max IS NULL OR v_max < 1 THEN
    PERFORM setval('users_id_seq', 1, false);
  ELSE
    PERFORM setval('users_id_seq', v_max, true);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'slippers_id_seq') THEN
    CREATE SEQUENCE slippers_id_seq OWNED BY "slippers"."id";
  END IF;
END $$;
ALTER TABLE "slippers" ALTER COLUMN "id" SET DEFAULT nextval('slippers_id_seq');
DO $$
DECLARE v_max bigint;
BEGIN
  SELECT MAX("id") INTO v_max FROM "slippers";
  IF v_max IS NULL OR v_max < 1 THEN
    PERFORM setval('slippers_id_seq', 1, false);
  ELSE
    PERFORM setval('slippers_id_seq', v_max, true);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'slipper_images_id_seq') THEN
    CREATE SEQUENCE slipper_images_id_seq OWNED BY "slipper_images"."id";
  END IF;
END $$;
ALTER TABLE "slipper_images" ALTER COLUMN "id" SET DEFAULT nextval('slipper_images_id_seq');
DO $$
DECLARE v_max bigint;
BEGIN
  SELECT MAX("id") INTO v_max FROM "slipper_images";
  IF v_max IS NULL OR v_max < 1 THEN
    PERFORM setval('slipper_images_id_seq', 1, false);
  ELSE
    PERFORM setval('slipper_images_id_seq', v_max, true);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'carts_id_seq') THEN
    CREATE SEQUENCE carts_id_seq OWNED BY "carts"."id";
  END IF;
END $$;
ALTER TABLE "carts" ALTER COLUMN "id" SET DEFAULT nextval('carts_id_seq');
DO $$
DECLARE v_max bigint;
BEGIN
  SELECT MAX("id") INTO v_max FROM "carts";
  IF v_max IS NULL OR v_max < 1 THEN
    PERFORM setval('carts_id_seq', 1, false);
  ELSE
    PERFORM setval('carts_id_seq', v_max, true);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'cart_items_id_seq') THEN
    CREATE SEQUENCE cart_items_id_seq OWNED BY "cart_items"."id";
  END IF;
END $$;
ALTER TABLE "cart_items" ALTER COLUMN "id" SET DEFAULT nextval('cart_items_id_seq');
DO $$
DECLARE v_max bigint;
BEGIN
  SELECT MAX("id") INTO v_max FROM "cart_items";
  IF v_max IS NULL OR v_max < 1 THEN
    PERFORM setval('cart_items_id_seq', 1, false);
  ELSE
    PERFORM setval('cart_items_id_seq', v_max, true);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'orders_id_seq') THEN
    CREATE SEQUENCE orders_id_seq OWNED BY "orders"."id";
  END IF;
END $$;
ALTER TABLE "orders" ALTER COLUMN "id" SET DEFAULT nextval('orders_id_seq');
DO $$
DECLARE v_max bigint;
BEGIN
  SELECT MAX("id") INTO v_max FROM "orders";
  IF v_max IS NULL OR v_max < 1 THEN
    PERFORM setval('orders_id_seq', 1, false);
  ELSE
    PERFORM setval('orders_id_seq', v_max, true);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'order_items_id_seq') THEN
    CREATE SEQUENCE order_items_id_seq OWNED BY "order_items"."id";
  END IF;
END $$;
ALTER TABLE "order_items" ALTER COLUMN "id" SET DEFAULT nextval('order_items_id_seq');
DO $$
DECLARE v_max bigint;
BEGIN
  SELECT MAX("id") INTO v_max FROM "order_items";
  IF v_max IS NULL OR v_max < 1 THEN
    PERFORM setval('order_items_id_seq', 1, false);
  ELSE
    PERFORM setval('order_items_id_seq', v_max, true);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'payments_id_seq') THEN
    CREATE SEQUENCE payments_id_seq OWNED BY "payments"."id";
  END IF;
END $$;
ALTER TABLE "payments" ALTER COLUMN "id" SET DEFAULT nextval('payments_id_seq');
DO $$
DECLARE v_max bigint;
BEGIN
  SELECT MAX("id") INTO v_max FROM "payments";
  IF v_max IS NULL OR v_max < 1 THEN
    PERFORM setval('payments_id_seq', 1, false);
  ELSE
    PERFORM setval('payments_id_seq', v_max, true);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'refund_requests_id_seq') THEN
    CREATE SEQUENCE refund_requests_id_seq OWNED BY "refund_requests"."id";
  END IF;
END $$;
ALTER TABLE "refund_requests" ALTER COLUMN "id" SET DEFAULT nextval('refund_requests_id_seq');
DO $$
DECLARE v_max bigint;
BEGIN
  SELECT MAX("id") INTO v_max FROM "refund_requests";
  IF v_max IS NULL OR v_max < 1 THEN
    PERFORM setval('refund_requests_id_seq', 1, false);
  ELSE
    PERFORM setval('refund_requests_id_seq', v_max, true);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'refunds_id_seq') THEN
    CREATE SEQUENCE refunds_id_seq OWNED BY "refunds"."id";
  END IF;
END $$;
ALTER TABLE "refunds" ALTER COLUMN "id" SET DEFAULT nextval('refunds_id_seq');
DO $$
DECLARE v_max bigint;
BEGIN
  SELECT MAX("id") INTO v_max FROM "refunds";
  IF v_max IS NULL OR v_max < 1 THEN
    PERFORM setval('refunds_id_seq', 1, false);
  ELSE
    PERFORM setval('refunds_id_seq', v_max, true);
  END IF;
END $$;
