-- Enforce unique constraints reflecting SQLite schema
ALTER TABLE "categories" ADD CONSTRAINT uq_categories_name UNIQUE ("name");

ALTER TABLE "carts" ADD CONSTRAINT uq_carts_user UNIQUE ("user_id");
ALTER TABLE "cart_items" ADD CONSTRAINT uq_cart_items_cart_slipper UNIQUE ("cart_id", "slipper_id");

ALTER TABLE "orders" ADD CONSTRAINT uq_orders_order_id UNIQUE ("order_id");
ALTER TABLE "orders" ADD CONSTRAINT uq_orders_transfer_id UNIQUE ("transfer_id");
ALTER TABLE "orders" ADD CONSTRAINT uq_orders_idempotency_key UNIQUE ("idempotency_key");

ALTER TABLE "payments" ADD CONSTRAINT uq_payments_shop_tx UNIQUE ("shop_transaction_id");

ALTER TABLE "users" ADD CONSTRAINT uq_users_phone UNIQUE ("phone_number");

ALTER TABLE "refunds" ADD CONSTRAINT uq_refunds_refund_id UNIQUE ("refund_id");

-- Foreign keys with actions matching SQLite
ALTER TABLE "cart_items"
  ADD CONSTRAINT fk_cart_items_cart FOREIGN KEY ("cart_id") REFERENCES "carts" ("id") ON DELETE CASCADE,
  ADD CONSTRAINT fk_cart_items_slipper FOREIGN KEY ("slipper_id") REFERENCES "slippers" ("id") ON DELETE CASCADE;

ALTER TABLE "carts"
  ADD CONSTRAINT fk_carts_user FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE;

ALTER TABLE "order_items"
  ADD CONSTRAINT fk_order_items_order FOREIGN KEY ("order_id") REFERENCES "orders" ("id") ON DELETE CASCADE,
  ADD CONSTRAINT fk_order_items_slipper FOREIGN KEY ("slipper_id") REFERENCES "slippers" ("id") ON DELETE CASCADE;

ALTER TABLE "orders"
  ADD CONSTRAINT fk_orders_user FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE;

ALTER TABLE "payments"
  ADD CONSTRAINT fk_payments_order FOREIGN KEY ("order_id") REFERENCES "orders" ("id") ON DELETE SET NULL;

ALTER TABLE "refund_requests"
  ADD CONSTRAINT fk_refreq_order FOREIGN KEY ("order_id") REFERENCES "orders" ("id") ON DELETE CASCADE,
  ADD CONSTRAINT fk_refreq_payment FOREIGN KEY ("payment_id") REFERENCES "payments" ("id") ON DELETE SET NULL,
  ADD CONSTRAINT fk_refreq_user FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE,
  ADD CONSTRAINT fk_refreq_admin FOREIGN KEY ("admin_id") REFERENCES "users" ("id") ON DELETE SET NULL;

ALTER TABLE "refunds"
  ADD CONSTRAINT fk_refunds_payment FOREIGN KEY ("payment_id") REFERENCES "payments" ("id") ON DELETE CASCADE,
  ADD CONSTRAINT fk_refunds_order FOREIGN KEY ("order_id") REFERENCES "orders" ("id") ON DELETE SET NULL,
  ADD CONSTRAINT fk_refunds_requested_by FOREIGN KEY ("requested_by") REFERENCES "users" ("id") ON DELETE CASCADE,
  ADD CONSTRAINT fk_refunds_processed_by FOREIGN KEY ("processed_by") REFERENCES "users" ("id") ON DELETE SET NULL;

ALTER TABLE "slipper_images"
  ADD CONSTRAINT fk_slipper_images_slipper FOREIGN KEY ("slipper_id") REFERENCES "slippers" ("id") ON DELETE CASCADE;

ALTER TABLE "slippers"
  ADD CONSTRAINT fk_slippers_category FOREIGN KEY ("category_id") REFERENCES "categories" ("id") ON DELETE SET NULL;

-- Non-unique indexes observed in SQLite (use IF NOT EXISTS to avoid duplicates)
CREATE INDEX IF NOT EXISTS idx_categories_active ON "categories" ("is_active");

CREATE INDEX IF NOT EXISTS idx_cart_items_cart ON "cart_items" ("cart_id");
CREATE INDEX IF NOT EXISTS idx_cart_items_slipper ON "cart_items" ("slipper_id");

CREATE INDEX IF NOT EXISTS idx_carts_created ON "carts" ("created_at");
CREATE INDEX IF NOT EXISTS idx_carts_user ON "carts" ("user_id");

CREATE INDEX IF NOT EXISTS idx_order_items_order ON "order_items" ("order_id");
CREATE INDEX IF NOT EXISTS idx_order_items_slipper ON "order_items" ("slipper_id");

CREATE INDEX IF NOT EXISTS idx_orders_payment_uuid ON "orders" ("payment_uuid");
CREATE INDEX IF NOT EXISTS idx_orders_user ON "orders" ("user_id");
CREATE INDEX IF NOT EXISTS idx_orders_user_status ON "orders" ("user_id", "status");
CREATE INDEX IF NOT EXISTS idx_orders_total_amount ON "orders" ("total_amount");
CREATE INDEX IF NOT EXISTS idx_orders_updated ON "orders" ("updated_at");
CREATE INDEX IF NOT EXISTS idx_orders_status ON "orders" ("status");
CREATE INDEX IF NOT EXISTS idx_orders_status_created ON "orders" ("status", "created_at");
CREATE INDEX IF NOT EXISTS idx_orders_created ON "orders" ("created_at");

CREATE INDEX IF NOT EXISTS idx_payments_order_status ON "payments" ("order_id", "status");
CREATE INDEX IF NOT EXISTS idx_payments_created ON "payments" ("created_at");
CREATE INDEX IF NOT EXISTS idx_payments_order_id ON "payments" ("order_id");
CREATE INDEX IF NOT EXISTS idx_payments_status ON "payments" ("status");
CREATE INDEX IF NOT EXISTS idx_payments_octo_uuid ON "payments" ("octo_payment_uuid");

CREATE INDEX IF NOT EXISTS idx_refund_order ON "refund_requests" ("order_id");
CREATE INDEX IF NOT EXISTS idx_refund_user ON "refund_requests" ("user_id");
CREATE INDEX IF NOT EXISTS idx_refund_order_status ON "refund_requests" ("order_id", "status");
CREATE INDEX IF NOT EXISTS idx_refund_status ON "refund_requests" ("status");

CREATE INDEX IF NOT EXISTS idx_refunds_status_created ON "refunds" ("status", "created_at");
CREATE INDEX IF NOT EXISTS idx_refunds_requester_status ON "refunds" ("requested_by", "status");
CREATE INDEX IF NOT EXISTS idx_refunds_payment_status ON "refunds" ("payment_id", "status");
CREATE INDEX IF NOT EXISTS idx_refunds_octo_uuid ON "refunds" ("octo_payment_uuid");
CREATE INDEX IF NOT EXISTS idx_refunds_created ON "refunds" ("created_at");
CREATE INDEX IF NOT EXISTS idx_refunds_status ON "refunds" ("status");
CREATE INDEX IF NOT EXISTS idx_refunds_processor ON "refunds" ("processed_by");
CREATE INDEX IF NOT EXISTS idx_refunds_requester ON "refunds" ("requested_by");
CREATE INDEX IF NOT EXISTS idx_refunds_order ON "refunds" ("order_id");
CREATE INDEX IF NOT EXISTS idx_refunds_payment ON "refunds" ("payment_id");

CREATE INDEX IF NOT EXISTS idx_slipper_images_primary_order ON "slipper_images" ("slipper_id", "is_primary", "order_index");
CREATE INDEX IF NOT EXISTS idx_slipper_images_slipper_id ON "slipper_images" ("slipper_id");
CREATE INDEX IF NOT EXISTS idx_slipper_images_order ON "slipper_images" ("order_index");
CREATE INDEX IF NOT EXISTS idx_slipper_images_primary ON "slipper_images" ("is_primary");

CREATE INDEX IF NOT EXISTS idx_slippers_price ON "slippers" ("price");
CREATE INDEX IF NOT EXISTS idx_slippers_category ON "slippers" ("category_id");
CREATE INDEX IF NOT EXISTS idx_slippers_name ON "slippers" ("name");
CREATE INDEX IF NOT EXISTS idx_slippers_quantity_active ON "slippers" ("quantity", "category_id");
CREATE INDEX IF NOT EXISTS idx_slippers_name_category ON "slippers" ("name", "category_id");
CREATE INDEX IF NOT EXISTS idx_slippers_quantity ON "slippers" ("quantity");
CREATE INDEX IF NOT EXISTS idx_slippers_created_at ON "slippers" ("created_at");
CREATE INDEX IF NOT EXISTS idx_slippers_size ON "slippers" ("size");

CREATE INDEX IF NOT EXISTS idx_users_name ON "users" ("name");
CREATE INDEX IF NOT EXISTS idx_users_admin_created ON "users" ("is_admin", "created_at");
CREATE INDEX IF NOT EXISTS idx_users_name_surname ON "users" ("name", "surname");
CREATE INDEX IF NOT EXISTS idx_users_admin ON "users" ("is_admin");
CREATE INDEX IF NOT EXISTS idx_users_created_at ON "users" ("created_at");
CREATE INDEX IF NOT EXISTS idx_users_surname ON "users" ("surname");
