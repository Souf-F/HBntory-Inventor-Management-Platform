# HBntory External Product API

This service is part of the HBntory student asset pack. It simulates a supplier catalog that your HBntory system can query.

The API is intentionally read-only. You are not expected to modify this service. Your task is to integrate with it from your own application.

## Data boundary

This API returns product catalog data only: identifiers, names, descriptions, categories, suppliers, prices, tags, and similar product metadata.

It does **not** return stock, reserved units, available units, reorder levels, or storage locations. Those values must be created, updated, listed, and persisted inside the HBntory application that you build.

## Run with Docker Compose

From this directory:

```bash
docker compose up --build
```

The API will be available at:

```text
http://localhost:5001
```

## Verify that it is running

```bash
curl http://localhost:5001/health
```

You can also run the included smoke test:

```bash
python3 scripts/smoke_test.py http://localhost:5001
```

## Main endpoints

- `GET /health`
- `GET /api/v1/products`
- `GET /api/v1/products/search?q=keyboard`
- `GET /api/v1/products/HB-LAP-1001`
- `GET /api/v1/categories`
- `GET /api/v1/suppliers`

For a full contract, read `docs/api_contract.md`.

## Integration notes

Your application should not assume that an external API is always available or always fast. Use the following query parameters to test integration robustness:

- `simulate_delay_ms=750`
- `force_error=true`

Example:

```bash
curl "http://localhost:5001/api/v1/products?simulate_delay_ms=750"
curl "http://localhost:5001/api/v1/products?force_error=true"
```

## Data

The catalog is stored in `data/products.json`. It includes products, suppliers, categories, prices, descriptions, brands, tags, and product metadata. Inventory quantities are intentionally excluded.
