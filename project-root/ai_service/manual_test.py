"""
Manual test script for the AI agent (task 5, step 2/3).

Usage:
    1. Start the real Product API (see product_mcp_server/README.md).
    2. Start the MCP server:  cd product_mcp_server && python server.py
    3. In another terminal, with GROQ_API_KEY set in .env:
           cd ai_service && python manual_test.py
"""

import asyncio

from agent import ask

QUESTIONS = [
    "Où puis-je trouver du café en grains 1kg ?",
    "Quel est le prix du 24 inch Compact Monitor ?",
    "Raconte-moi une blague.",
]


async def main() -> None:
    for question in QUESTIONS:
        print(f"\n=== {question} ===")
        answer = await ask(question)
        print(answer)


if __name__ == "__main__":
    asyncio.run(main())
