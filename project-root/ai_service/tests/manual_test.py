"""
Manual test script for the AI agent (task 5, step 2/3).

Superseded for regular use by test_agent_live.py (same questions, but
with automatic pass/fail assertions instead of output you read by eye).
Kept for a quick, readable, human-eyeballed sanity check when you want
to see the full model reasoning and tool calls scroll by.

Usage:
    1. Start the real Product API (see product_mcp_server/README.md).
    2. Start the MCP server:  cd product_mcp_server && python server.py
    3. In another terminal, with GROQ_API_KEY set in .env:
           cd ai_service && python -m tests.manual_test
"""

import asyncio

from agent import ask

QUESTIONS = [
    # Type 1: product details
    "Quel est le prix du 24 inch Compact Monitor ?",
    # Type 1, product not in the catalog: must say so, not invent a price
    "Où puis-je trouver du café en grains 1kg ?",
    # Type 2: where is a product available
    "Où puis-je trouver le 24 inch Compact Monitor en stock ?",
    # Type 3: what's available in one branch
    "Quels produits sont disponibles dans la branche HBntory Paris ?",
    # Type 3, branch doesn't exist: must say so, not invent a stock list
    "Quels produits sont disponibles dans la branche de Bordeaux ?",
    # Type 4: shopping list feasibility
    "Si j'ai besoin de 5 24 inch Compact Monitor, quelle branche peut me les fournir ?",
    # Out of scope: must decline, not call any tool
    "Raconte-moi une blague.",
]


async def main() -> None:
    for question in QUESTIONS:
        print(f"\n=== {question} ===")
        answer = await ask(question)
        print(answer)


if __name__ == "__main__":
    asyncio.run(main())
