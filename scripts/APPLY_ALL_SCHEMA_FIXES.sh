#!/bin/bash
# Emergency fix script for both orders and payments schema issues
# Run this on production server: ubuntu@ip-172-31-26-54

set -e  # Exit on any error

echo "=========================================="
echo "Emergency Schema Fix - Orders & Payments"
echo "=========================================="
echo ""

# Database connection details
DB_USER="slipper_user"
DB_NAME="slippers"

echo "Step 1: Fixing orders table (add status column)..."
psql -U "$DB_USER" -d "$DB_NAME" -f scripts/fix_orders_schema.sql

echo ""
echo "Step 2: Fixing payments table (add status column)..."
psql -U "$DB_USER" -d "$DB_NAME" -f scripts/fix_payments_schema.sql

echo ""
echo "Step 3: Verifying orders table schema..."
psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'orders' AND column_name = 'status';"

echo ""
echo "Step 4: Verifying payments table schema..."
psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'payments' AND column_name = 'status';"

echo ""
echo "=========================================="
echo "Schema fixes applied successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Restart the service: sudo systemctl restart slippers"
echo "2. Check status: sudo systemctl status slippers"
echo "3. Monitor logs: sudo journalctl -u slippers -f"
