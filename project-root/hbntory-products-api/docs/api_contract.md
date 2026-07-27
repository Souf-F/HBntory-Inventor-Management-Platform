# HBntory External Product API Contract

This API is a simulated external supplier catalog. It is intentionally read-only. Your HBntory implementation should consume it as an external dependency.

## Data boundary

The API exposes product catalog metadata only. It does not expose inventory state.

The HBntory application developed by students is responsible for:

- creating local inventory records;
- updating local stock quantities;
- listing local inventory state;
- recording stock movements or adjustments;
- deciding how imported supplier metadata maps to internal product records.

Do not design your HBntory database as if the supplier API owned your stock values. The supplier API can tell you what a product is; your application must decide how many units you manage and how that quantity changes.

## Base URL

When using Docker Compose from this asset pack:

```text
http://localhost:5001
```

When another container needs to call this service inside the same Compose network:

```text
http://external-products-api:5000
```

## Required integration behaviors

Your HBntory application should handle the following cases correctly:

- The supplier API returns an empty product list.
- A product detail request returns `404`.
- The supplier API responds slowly. You can simulate this with `simulate_delay_ms`.
- The supplier API is temporarily unavailable. You can simulate this with `force_error=true`.
- Supplier product metadata may change over time. Avoid silently overwriting internal inventory values when refreshing supplier data.

## Useful endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Check whether the external service is reachable. |
| GET | `/api/v1/products` | List products, with optional filters and pagination. |
| GET | `/api/v1/products/search?q=keyboard` | Search by name, SKU, description, or tag. |
| GET | `/api/v1/products/{id_or_sku}` | Retrieve one product by numeric id or SKU. |
| GET | `/api/v1/categories` | Retrieve category names and product counts. |
| GET | `/api/v1/suppliers` | Retrieve supplier metadata. |

## Query parameters for `/api/v1/products`

| Parameter | Type | Example | Description |
| --- | --- | --- | --- |
| `q` | string | `q=keyboard` | Search text matched against name, SKU, description, and tags. |
| `category` | string | `category=Accessories` | Exact category filter. |
| `supplier_id` | string | `supplier_id=SUP-HBT-001` | Exact supplier filter. |
| `include_discontinued` | boolean | `include_discontinued=true` | Include discontinued catalog products. Default: `false`. |
| `min_price` | number | `min_price=50` | Minimum unit price. |
| `max_price` | number | `max_price=200` | Maximum unit price. |
| `limit` | integer | `limit=20` | Page size. Maximum: 100. |
| `offset` | integer | `offset=20` | Result offset. |
| `sort` | string | `sort=-unit_price` | Sort field. Prefix with `-` for descending order. Supported fields: `name`, `sku`, `category`, `unit_price`, `updated_at`. |

## Example product object

```json
{
  "id": 1,
  "sku": "HB-LAP-1001",
  "name": "Holberton Student Laptop 14",
  "description": "Training catalog item for HBntory integration: holberton student laptop 14.",
  "category": "Laptops",
  "brand": "Holberton",
  "supplier_id": "SUP-HBT-001",
  "supplier_name": "Holberton Tools Co.",
  "unit_price": 799.0,
  "currency": "USD",
  "discontinued": false,
  "weight_kg": 1.35,
  "tags": ["student", "portable", "linux-ready"],
  "updated_at": "2026-05-22T12:00:00Z"
}
```

## Error format

Error responses use this shape:

```json
{
  "error": "not_found",
  "message": "Product not found."
}
```
