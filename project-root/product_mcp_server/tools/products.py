from fastmcp.exceptions import ToolError
from pydantic import BaseModel

from mcp_instance import mcp
from product_api_client import (
    ProductAPIError,
    ProductNotFoundError,
    get_product,
    list_products as _fetch_products,
)


class ProductSummary(BaseModel):
    """Minimal product info for browsing a list — no unnecessary fields."""

    product_id: str
    name: str
    price: float


class ProductDetails(BaseModel):
    """Full product info for a single lookup."""

    product_id: str
    name: str
    description: str
    price: float


def _to_summary(raw: dict) -> ProductSummary:
    try:
        return ProductSummary(
            product_id=raw["sku"], name=raw["name"], price=raw["unit_price"]
        )
    except KeyError as exc:
        raise ToolError(f"Product API returned a malformed product (missing {exc}).")


def _to_details(raw: dict) -> ProductDetails:
    try:
        return ProductDetails(
            product_id=raw["sku"],
            name=raw["name"],
            description=raw.get("description", ""),
            price=raw["unit_price"],
        )
    except KeyError as exc:
        raise ToolError(f"Product API returned a malformed product (missing {exc}).")


@mcp.tool()
def list_products(category: str | None = None, limit: int = 20) -> list[ProductSummary]:
    """
    List available products from the catalog.

    Args:
        category: optional category filter.
        limit: max number of products to return (default 20).

    Returns a list of product summaries (product_id, name, price).
    """
    filters = {"limit": limit}
    if category:
        filters["category"] = category

    try:
        raw_products = _fetch_products(**filters)
    except ProductAPIError as exc:
        raise ToolError(f"Could not list products: {exc}")

    return [_to_summary(p) for p in raw_products]


@mcp.tool()
def get_product_details(product_id: str) -> ProductDetails:
    """
    Get full details (name, description, price) for one product.

    Args:
        product_id: the product's external identifier (same value stored
            as Stock.product_id in our database; called "sku" by the
            Product API itself).

    Raises a tool error if the product_id is unknown or the Product API
    is unreachable — never returns invented data.
    """
    try:
        raw_product = get_product(product_id)
    except ProductNotFoundError:
        raise ToolError(f"No product found with product_id '{product_id}'.")
    except ProductAPIError as exc:
        raise ToolError(f"Could not fetch product '{product_id}': {exc}")

    return _to_details(raw_product)