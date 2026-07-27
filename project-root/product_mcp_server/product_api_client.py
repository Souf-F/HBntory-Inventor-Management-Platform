"""
Thin, framework-agnostic HTTP client for the external Product API
(https://github.com/hbtn-edu/hbntory-products-api).

Deliberately independent from backoffice/app/product_api.py: this module
runs inside the MCP server's own container/process, not inside Flask, so
it can't rely on `flask.current_app`. Same contract, separate client.
"""

import os

import requests

PRODUCT_API_URL = os.environ.get("PRODUCT_API_URL", "http://localhost:5001")


class ProductAPIError(Exception):
    """Raised when the Product API is unreachable or returns an error."""


class ProductNotFoundError(ProductAPIError):
    """Raised when the Product API returns 404 for a given sku/id."""


def _get(path: str, params: dict | None = None, timeout: float = 3.0) -> dict:
    url = f"{PRODUCT_API_URL}{path}"
    try:
        response = requests.get(url, params=params, timeout=timeout)
    except requests.exceptions.Timeout:
        raise ProductAPIError("Product API timed out.")
    except requests.exceptions.ConnectionError:
        raise ProductAPIError("Product API is unreachable.")

    if response.status_code == 404:
        raise ProductNotFoundError(f"No product found for '{path}'.")
    if not response.ok:
        raise ProductAPIError(f"Product API returned status {response.status_code}.")

    return response.json()


def list_products(**filters) -> list[dict]:
    """Raw product list from the API (category, limit, offset, ... as filters)."""
    data = _get("/api/v1/products", params=filters)
    return data.get("results", data if isinstance(data, list) else [])


def get_product(sku_or_id: str) -> dict:
    """Raw product details. Raises ProductNotFoundError if unknown."""
    return _get(f"/api/v1/products/{sku_or_id}")


def search_products(query: str) -> list[dict]:
    """Raw product list matching a free-text search (name, sku, tags...)."""
    data = _get("/api/v1/products/search", params={"q": query})
    return data.get("results", data if isinstance(data, list) else [])