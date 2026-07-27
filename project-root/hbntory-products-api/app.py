#!/usr/bin/env python3
"""HBntory External Product API.

This service simulates an external supplier catalog. It is intentionally
read-only: students should integrate with it from their own HBntory system,
not modify it as part of the project.

Important data boundary:
- This API exposes product catalog metadata only.
- Inventory state such as stock, reserved units, available units, reorder
  levels, and storage locations belongs to the HBntory application built by
  students.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
import json
import os
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.environ.get(
    "HBN_PRODUCTS_DATA_FILE",
    os.path.join(BASE_DIR, "data", "products.json"),
)
HOST = os.environ.get("HBN_PRODUCTS_HOST", "0.0.0.0")
PORT = int(os.environ.get("HBN_PRODUCTS_PORT", "5000"))
DEFAULT_LATENCY_MS = int(os.environ.get("HBN_PRODUCTS_LATENCY_MS", "0"))
MAX_LIMIT = 100


def load_catalog():
    with open(DATA_FILE, "r", encoding="utf-8") as data_file:
        return json.load(data_file)


CATALOG = load_catalog()
PRODUCTS = CATALOG["products"]
SUPPLIERS = CATALOG["suppliers"]
SUPPLIER_BY_ID = {supplier["id"]: supplier for supplier in SUPPLIERS}


def parse_bool(value):
    if value is None:
        return None
    normalized = value.lower().strip()
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n"}:
        return False
    return None


def to_int(value, default, minimum=None, maximum=None):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    if minimum is not None:
        parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_product(product, include_supplier=False):
    result = dict(product)
    if include_supplier:
        result["supplier"] = SUPPLIER_BY_ID.get(product["supplier_id"])
    return result


def filter_products(query_params):
    results = list(PRODUCTS)

    q = (query_params.get("q", [""])[0] or "").strip().lower()
    category = (query_params.get("category", [""])[0] or "").strip().lower()
    supplier_id = (query_params.get("supplier_id", [""])[0] or "").strip().lower()
    include_discontinued = parse_bool(query_params.get("include_discontinued", ["false"])[0])
    min_price = to_float(query_params.get("min_price", [None])[0])
    max_price = to_float(query_params.get("max_price", [None])[0])

    if not include_discontinued:
        results = [product for product in results if not product["discontinued"]]

    if q:
        results = [
            product for product in results
            if q in product["name"].lower()
            or q in product["sku"].lower()
            or q in product["description"].lower()
            or any(q in tag.lower() for tag in product["tags"])
        ]

    if category:
        results = [product for product in results if product["category"].lower() == category]

    if supplier_id:
        results = [product for product in results if product["supplier_id"].lower() == supplier_id]

    if min_price is not None:
        results = [product for product in results if product["unit_price"] >= min_price]

    if max_price is not None:
        results = [product for product in results if product["unit_price"] <= max_price]

    sort = (query_params.get("sort", ["name"])[0] or "name").strip().lower()
    reverse = False
    if sort.startswith("-"):
        reverse = True
        sort = sort[1:]
    if sort in {"name", "sku", "category", "unit_price", "updated_at"}:
        results.sort(key=lambda product: product[sort], reverse=reverse)

    return results


class Handler(BaseHTTPRequestHandler):
    server_version = "HBntoryExternalProductAPI/1.1"

    def log_message(self, fmt, *args):
        print("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), fmt % args))

    def _send_json(self, status_code, payload, extra_headers=None):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("X-External-Service", "HBntory Supplier Catalog")
        self.send_header("X-RateLimit-Limit", "120")
        self.send_header("X-RateLimit-Policy", "simulated; not enforced")
        if extra_headers:
            for name, value in extra_headers.items():
                self.send_header(name, str(value))
        self.end_headers()
        self.wfile.write(body)

    def _not_found(self, message="Resource not found"):
        self._send_json(404, {"error": "not_found", "message": message})

    def _bad_request(self, message):
        self._send_json(400, {"error": "bad_request", "message": message})

    def do_OPTIONS(self):
        self._send_json(204, {})

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query_params = parse_qs(parsed.query)

        latency_ms = to_int(query_params.get("simulate_delay_ms", [DEFAULT_LATENCY_MS])[0], DEFAULT_LATENCY_MS, 0, 3000)
        if latency_ms:
            time.sleep(latency_ms / 1000)

        if parse_bool(query_params.get("force_error", ["false"])[0]):
            self._send_json(503, {"error": "supplier_unavailable", "message": "Forced simulation error."})
            return

        if path in {"/", "/api", "/api/v1"}:
            self._send_json(200, {
                "service": "HBntory External Product API",
                "version": "1.1.0",
                "documentation": "/api/v1/meta",
                "data_boundary": "Product catalog metadata only. Inventory quantities are managed by HBntory.",
                "endpoints": [
                    "/health",
                    "/api/v1/products",
                    "/api/v1/products/search?q=keyboard",
                    "/api/v1/products/HB-LAP-1001",
                    "/api/v1/categories",
                    "/api/v1/suppliers",
                ],
            })
            return

        if path == "/health":
            self._send_json(200, {"status": "ok", "products": len(PRODUCTS), "suppliers": len(SUPPLIERS)})
            return

        if path == "/api/v1/meta":
            self._send_json(200, {
                "service": "HBntory External Product API",
                "purpose": "Read-only supplier catalog for HBntory integration exercises.",
                "version": "1.1.0",
                "data_source": os.path.basename(DATA_FILE),
                "data_boundary": "This API exposes product catalog metadata only. Stock, reserved units, available units, reorder levels, and storage locations must be handled inside the HBntory application.",
                "supported_filters": ["q", "category", "supplier_id", "include_discontinued", "min_price", "max_price"],
                "supported_sort_fields": ["name", "sku", "category", "unit_price", "updated_at"],
            })
            return

        if path == "/api/v1/products" or path == "/api/v1/products/search":
            filtered = filter_products(query_params)
            limit = to_int(query_params.get("limit", [20])[0], 20, 1, MAX_LIMIT)
            offset = to_int(query_params.get("offset", [0])[0], 0, 0, None)
            page = filtered[offset:offset + limit]
            self._send_json(200, {
                "count": len(filtered),
                "limit": limit,
                "offset": offset,
                "results": [normalize_product(product) for product in page],
            })
            return

        if path == "/api/v1/categories":
            categories = {}
            for product in PRODUCTS:
                categories.setdefault(product["category"], {"name": product["category"], "product_count": 0})
                categories[product["category"]]["product_count"] += 1
            self._send_json(200, {"count": len(categories), "results": sorted(categories.values(), key=lambda item: item["name"])})
            return

        if path == "/api/v1/suppliers":
            self._send_json(200, {"count": len(SUPPLIERS), "results": SUPPLIERS})
            return

        prefix = "/api/v1/products/"
        if path.startswith(prefix):
            identifier = path[len(prefix):].strip().lower()
            if not identifier:
                self._bad_request("A product id or SKU is required.")
                return
            product = next(
                (
                    item for item in PRODUCTS
                    if str(item["id"]).lower() == identifier or item["sku"].lower() == identifier
                ),
                None,
            )
            if product is None:
                self._not_found("Product not found.")
                return
            self._send_json(200, normalize_product(product, include_supplier=True))
            return

        self._not_found()


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"HBntory External Product API running on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
