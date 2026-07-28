# Product MCP Server

Bridges the AI agent to the external Product API and to the shared
database's stock. Exposes MCP tools so the agent can look up product and
stock information without ever inventing it.

## Running

```bash
cd product_mcp_server
pip install -r requirements.txt
python server.py
```

Reads `PRODUCT_API_URL` from the environment (defaults to
`http://localhost:5001`) and `DATABASE_URL` for the shared database
(defaults to the Backoffice's local SQLite file). The MCP server itself
listens on `MCP_PORT` (defaults to `8000`), transport `streamable-http`.

## Product tools

### `list_products(category: str | None = None, limit: int = 20) -> list[ProductSummary]`

Returns a lightweight summary per product (`product_id`, `name`, `price`),
not the full Product API payload. Optional `category` filter.

### `search_products(query: str, limit: int = 20) -> list[ProductSummary]`

Free-text search by name (or sku, tag, description). Use this to find a
product's `product_id` when only its name is known, instead of guessing a
`category` filter for `list_products`.

### `get_product_details(product_id: str) -> ProductDetails`

Returns full details for one product (`product_id`, `name`, `description`,
`price`). `product_id` is the same value stored as `Stock.product_id` in
the database (the Product API itself calls this field `sku`).

Only these fields are exposed on purpose (task requirement: "avoid exposing
unnecessary Product API behavior"). The Product API also returns `category`,
`brand`, `supplier_id`, `supplier_name`, `currency`, `weight_kg`, `tags`,
`discontinued`, none of which the agent needs to answer stock questions.

## Stock tools

Read-only access to the shared database, via `db.py`, which imports
`Branch`/`Stock` directly from `backoffice/app/models.py` instead of
duplicating the schema (see `architecture.md`, Decision 2). This uses a
plain SQLAlchemy session bound to its own engine, not Flask-SQLAlchemy's
`db.session`, since this process never runs inside a Flask app context.

### `check_stock(product_id: str, branch_name: str | None = None) -> list[BranchStockLevel]`

How much of one product is in stock, across all branches or in one named
branch.

### `list_branch_stock(branch_name: str) -> list[BranchProduct]`

Every product currently in stock in one branch, with quantities.

### `check_shopping_list(items: list[ShoppingListItem]) -> list[BranchFeasibility]`

For each branch, whether that branch alone holds enough stock to fulfill
every item on the list (no aggregation across branches).

All three raise a `ToolError` for an unknown branch name (never guessed or
fuzzy-matched: branch names must match exactly, e.g. `HBntory Paris`), and
return an empty list (not an error) when a product/branch exists but
simply has no matching stock.

## Error handling

Two layers, each with one job:

**`product_api_client.py`**: talks HTTP to the Product API. Every failure
mode is caught and turned into one of two exception types, so callers never
have to deal with `requests` exceptions directly:

| Product API behavior              | Raised as              |
|-----------------------------------|-------------------------|
| Connection refused / API down     | `ProductAPIError("Product API is unreachable.")` |
| Request takes too long (3s)       | `ProductAPIError("Product API timed out.")` |
| `404` (unknown product/sku)       | `ProductNotFoundError(...)` (subclass of `ProductAPIError`) |
| Any other non-2xx status          | `ProductAPIError("Product API returned status <code>.")` |

**`tools/products.py`** and **`tools/stock.py`**: catch those exceptions
(and DB lookup failures) at the tool boundary and re-raise them as
`fastmcp.exceptions.ToolError` with a human-readable message. `ToolError`
is FastMCP's mechanism for "this is an expected, recoverable failure": the
AI agent receives the message as the tool's result and can react to it
(e.g. tell the user "I couldn't find that product"), instead of the
server crashing or returning malformed data.

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
cases for the product tools, plus the 3 stock tools against the seeded
database (`backoffice/app/seed.py`):

1. **Successful listing**: `list_products` returns real catalog entries.
2. **Successful detail lookup**: `get_product_details` on a valid id
   returns the full product.
3. **Invalid product identifier**: `get_product_details("does-not-exist")`
   raises a `ToolError` with a clear "not found" message instead of
   crashing.
4. **Product API down**: stop `app.py` and re-run; any tool call raises a
   `ToolError` with `"Product API is unreachable."` instead of hanging or
   crashing the MCP server.
5. **Stock tools**: `check_stock`, `list_branch_stock`, and
   `check_shopping_list` against known seeded values (e.g. `HB-MON-2102`
   in `HBntory Paris`, quantity 40), including an unknown branch name.

### Evidence (manual run, 2026-07-23)

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

=== check_stock (all branches) ===
[Root(branch_name='HBntory Paris', quantity=40)]

=== check_stock (unknown branch) ===
Got expected tool error: No branch found with name 'Does Not Exist'.

=== list_branch_stock ===
[Root(product_id='HB-KBD-4102', quantity=70), Root(product_id='HB-LAP-1001', quantity=10),
 Root(product_id='HB-MIC-5201', quantity=100), Root(product_id='HB-MON-2102', quantity=40)]

=== check_shopping_list (satisfiable in HBntory Paris) ===
[Root(branch_name='HBntory Paris', can_fulfill=True, missing_product_ids=[]),
 Root(branch_name='HBntory Lyon', can_fulfill=False, missing_product_ids=['HB-MON-2102', 'HB-KBD-4102']),
 Root(branch_name='HBntory Marseille', can_fulfill=False, missing_product_ids=['HB-MON-2102', 'HB-KBD-4102'])]
```