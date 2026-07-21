"""
HBntory — Product API client.

Thin wrapper around the external Product API
(https://github.com/hbtn-edu/hbntory-products-api).

Golden rule reminder: nothing returned by this module is ever persisted in
the local database. It is only used to display product information on the
fly (see architecture.md, section 3). Only the `sku` field should ever be
stored locally, as `Stock.product_id`.

The API is read-only and exposes product catalog metadata only — it never
returns stock/quantity data. That's entirely owned by our own database.

This module is defensive on purpose: the API's own docs explicitly say to
handle an unreachable service, a slow response, and a 404 gracefully
(see docs/api_contract.md, "Required integration behaviors").
"""

import requests
from flask import current_app


class ProductAPIError(Exception):
    """Raised when the Product API is unreachable or returns an error."""


def _base_url() -> str:
    return current_app.config["PRODUCT_API_URL"]


def _get(path: str, params: dict | None = None, timeout: float = 3.0) -> dict:
    """
    Shared GET helper. Raises ProductAPIError on any failure so callers
    only have to handle one exception type, instead of juggling
    requests.Timeout, requests.ConnectionError, etc. separately.
    """
    url = f"{_base_url()}{path}"
    try:
        response = requests.get(url, params=params, timeout=timeout)
    except requests.exceptions.Timeout:
        raise ProductAPIError("Product API timed out.")
    except requests.exceptions.ConnectionError:
        raise ProductAPIError("Product API is unreachable.")

    if response.status_code == 404:
        raise ProductAPIError("Product not found.")
    if not response.ok:
        raise ProductAPIError(f"Product API returned status {response.status_code}.")

    return response.json()


def health_check() -> bool:
    """True if the Product API is reachable, False otherwise (never raises)."""
    try:
        _get("/health", timeout=2.0)
        return True
    except ProductAPIError:
        return False


def list_products(**filters) -> list[dict]:
    """
    List products from the catalog, with optional filters passed straight
    through as query parameters (category, supplier_id, min_price,
    max_price, limit, offset, sort — see api_contract.md).

    Returns an empty list if the API has nothing to show — this is an
    explicitly expected case, not an error.
    """
    data = _get("/api/v1/products", params=filters)
    return data.get("results", [])


def search_products(query: str) -> list[dict]:
    """Search products by name, SKU, description, or tag."""
    data = _get("/api/v1/products/search", params={"q": query})
    return data.get("results", [])


def get_product(sku_or_id) -> dict | None:
    """
    Retrieve one product by SKU (preferred — this is what we store as
    Stock.product_id) or numeric id. Returns None if not found, rather
    than raising, since "product no longer in the catalog" is a normal
    case a template needs to handle gracefully (see api_contract.md:
    "Supplier product metadata may change over time").
    """
    try:
        return _get(f"/api/v1/products/{sku_or_id}")
    except ProductAPIError:
        return None