#!/usr/bin/env python3
"""Basic smoke test for the HBntory External Product API."""

from urllib.request import urlopen
from urllib.error import HTTPError, URLError
import json
import sys

BASE_URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:5001"
FORBIDDEN_INVENTORY_FIELDS = {
    "stock",
    "reserved",
    "available",
    "reorder_level",
    "low_stock",
    "location_hint",
}


def get_json(path):
    url = f"{BASE_URL}{path}"
    try:
        with urlopen(url, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))
    except URLError as exc:
        raise SystemExit(f"Could not connect to {url}: {exc}")


def assert_no_inventory_fields(payload):
    products = []
    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        products = payload["results"]
    elif isinstance(payload, dict) and "sku" in payload:
        products = [payload]
    for product in products:
        leaked = FORBIDDEN_INVENTORY_FIELDS.intersection(product.keys())
        if leaked:
            raise SystemExit(f"External API leaked inventory fields: {sorted(leaked)}")


checks = [
    ("/health", 200),
    ("/api/v1/products?limit=3", 200),
    ("/api/v1/products/search?q=keyboard", 200),
    ("/api/v1/products/HB-LAP-1001", 200),
    ("/api/v1/products/UNKNOWN-SKU", 404),
]

for path, expected_status in checks:
    status, payload = get_json(path)
    print(f"{path}: HTTP {status}")
    if status != expected_status:
        print(json.dumps(payload, indent=2))
        raise SystemExit(f"Expected HTTP {expected_status}, got HTTP {status}")
    assert_no_inventory_fields(payload)

print("Smoke test passed.")
