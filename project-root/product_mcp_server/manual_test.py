"""
Manual test script for the Product MCP server (task 4, step 3).

Usage:
    1. Start the real Product API (see its own README).
    2. Start this MCP server:  python server.py
    3. In another terminal:    python manual_test.py

Covers the 4 required cases:
    - successful product listing
    - successful product detail lookup
    - invalid product identifier (404 from the Product API)
    - Product API connection error (stop the Product API and re-run)
"""

import asyncio
import os

from fastmcp import Client

MCP_URL = os.environ.get("MCP_URL", "http://localhost:8000/mcp")


async def main() -> None:
    async with Client(MCP_URL) as client:
        print("=== list_products ===")
        result = await client.call_tool("list_products", {"limit": 5})
        print(result.data)

        print("\n=== get_product_details (valid id) ===")
        products = result.data
        if products:
            first_id = products[0].product_id
            result = await client.call_tool(
                "get_product_details", {"product_id": first_id}
            )
            print(result.data)
        else:
            print("No products returned by list_products — skipping.")

        print("\n=== get_product_details (invalid id) ===")
        try:
            await client.call_tool(
                "get_product_details", {"product_id": "does-not-exist"}
            )
        except Exception as exc:
            print(f"Got expected tool error: {exc}")

        print(
            "\n=== Product API down ===\n"
            "Stop the Product API container now, then re-run get_product_details "
            "manually to confirm a clear connection-error message (not a crash)."
        )


if __name__ == "__main__":
    asyncio.run(main())