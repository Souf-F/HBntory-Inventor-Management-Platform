# Product MCP Server

Bridges the AI agent to the external Product API. Exposes MCP tools so the
agent can look up product information without ever inventing it.

## Running

```bash
pip install -r requirements.txt
python server.py
```

Reads `PRODUCT_API_URL` from the environment (defaults to
`http://localhost:5001`). The MCP server itself listens on
`MCP_PORT` (defaults to `8000`), transport `streamable-http`.

## Tools

### `list_products(category: str | None = None, limit: int = 20) -> list[ProductSummary]`

Returns a lightweight summary per product (`product_id`, `name`, `price`),
not the full Product API payload. Optional `category` filter.

### `get_product_details(product_id: str) -> ProductDetails`

Returns full details for one product (`product_id`, `name`, `description`,
`price`). `product_id` is the same value stored as `Stock.product_id` in our
database (the Product API itself calls this field `sku`).

Only these fields are exposed on purpose (task requirement: "avoid exposing
unnecessary Product API behavior"). The Product API also returns `category`,
`brand`, `supplier_id`, `supplier_name`, `currency`, `weight_kg`, `tags`,
`discontinued`, none of which the agent needs to answer stock questions.

## Error handling

Two layers, each with one job:

**`product_api_client.py`**: talks HTTP to the Product API. Every failure
mode is caught and turned into one of two exception types, so callers never
have to deal with `requests` exceptions directly:

| Product API API behavior         | Raised as              |
|-----------------------------------|-------------------------|
| Connection refused / API down     | `ProductAPIError("Product API is unreachable.")` |
| Request takes too long (3s)       | `ProductAPIError("Product API timed out.")` |
| `404` (unknown product/sku)       | `ProductNotFoundError(...)` (subclass of `ProductAPIError`) |
| Any other non-2xx status          | `ProductAPIError("Product API returned status <code>.")` |

**`tools/products.py`**: catches those exceptions at the tool boundary and
re-raises them as `fastmcp.exceptions.ToolError` with a human-readable
message. `ToolError` is FastMCP's mechanism for "this is an expected,
recoverable failure": the AI agent receives the message as the tool's
result and can react to it (e.g. tell the user "I couldn't find that
product" or "the product catalog is temporarily unavailable"), instead of
the server crashing or returning malformed data.

A third case is also handled: if the Product API is reachable but returns a
product missing an expected field (`sku`, `name`, `unit_price`), the mapping
functions (`_to_summary`, `_to_details`) catch the `KeyError` and raise a
`ToolError` too, rather than propagating a raw exception or silently
returning partial/incorrect data.

In every case, the rule is the same: **never invent data, never fail
silently, always surface a clear reason the agent (and ultimately the end
user) can act on.**

## Manual testing (see `manual_test.py`)

Run the real Product API (`hbntory-products-api`, `python3 app.py`), then
this MCP server, then `python manual_test.py`. It exercises all 4 required
cases:

1. **Successful listing**: `list_products` returns real catalog entries.
2. **Successful detail lookup**: `get_product_details` on a valid id
   returns the full product.
3. **Invalid product identifier**: `get_product_details("does-not-exist")`
   raises a `ToolError` with a clear "not found" message instead of
   crashing.
4. **Product API down**: stop `app.py` and re-run; any tool call raises a
   `ToolError` with `"Product API is unreachable."` instead of hanging or
   crashing the MCP server.

### Evidence (manual run, 2026-07-22)

```
=== list_products ===
[Root(product_id='HB-MON-2102', name='24 inch Compact Monitor', price=169.99), ...]

=== get_product_details (valid id) ===
Root(product_id='HB-MON-2102', name='24 inch Compact Monitor',
     description='Training catalog item for HBntory integration: 24 inch compact monitor.',
     price=169.99)

=== get_product_details (invalid id) ===
Got expected tool error: No product found with product_id 'does-not-exist'.

=== Product API down ===
fastmcp.exceptions.ToolError: Could not list products: Product API is unreachable.
```