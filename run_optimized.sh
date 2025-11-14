#!/bin/bash
# High-Performance Production Startup Script for Slippers API
# This script starts the application with all performance optimizations enabled

set -e

echo "🚀 Starting Slippers API in HIGH-PERFORMANCE mode"
echo "================================================="

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please create it first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Install performance dependencies if not present
echo "📦 Checking performance dependencies..."
pip list | grep -q "uvloop" || pip install uvloop
pip list | grep -q "httptools" || pip install httptools

# Set production environment variables
export PYTHONOPTIMIZE=2  # Enable Python optimizations (remove docstrings, assertions)
export PYTHONDONTWRITEBYTECODE=1  # Don't write .pyc files
export PYTHONUNBUFFERED=1  # Unbuffered output

# Detect optimal worker count (2-4 x CPU cores for I/O-bound apps)
CPU_CORES=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 2)
WORKERS=$((CPU_CORES * 2))

# Cap workers at reasonable maximum
if [ $WORKERS -gt 16 ]; then
    WORKERS=16
fi

echo "🖥️  CPU Cores: $CPU_CORES"
echo "👷 Workers: $WORKERS"
echo ""

# Launch with optimized settings
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers $WORKERS \
    --loop uvloop \
    --http httptools \
    --backlog 4096 \
    --limit-concurrency 10000 \
    --limit-max-requests 100000 \
    --timeout-keep-alive 5 \
    --no-access-log \
    --log-level warning

# Performance flags explained:
# --loop uvloop: Ultra-fast event loop (2-4x faster than asyncio)
# --http httptools: Fast HTTP parser
# --backlog 4096: TCP connection queue size
# --limit-concurrency: Max simultaneous connections per worker
# --limit-max-requests: Auto-restart worker after N requests (prevents memory leaks)
# --timeout-keep-alive: Close idle connections after 5s
# --no-access-log: Disable access logs for performance (use nginx logs instead)
# --log-level warning: Reduce logging overhead
