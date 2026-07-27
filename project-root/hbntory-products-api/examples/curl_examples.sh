#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:5001}"

echo "Health check"
curl -s "${BASE_URL}/health" | python3 -m json.tool

echo "List first 5 catalog products"
curl -s "${BASE_URL}/api/v1/products?limit=5" | python3 -m json.tool

echo "Search products by name, SKU, description, or tag"
curl -s "${BASE_URL}/api/v1/products/search?q=keyboard" | python3 -m json.tool

echo "Filter products by category"
curl -s "${BASE_URL}/api/v1/products?category=Accessories&sort=name" | python3 -m json.tool

echo "Filter products by price range"
curl -s "${BASE_URL}/api/v1/products?min_price=50&max_price=200&sort=unit_price" | python3 -m json.tool

echo "Get product details by SKU"
curl -s "${BASE_URL}/api/v1/products/HB-LAP-1001" | python3 -m json.tool
