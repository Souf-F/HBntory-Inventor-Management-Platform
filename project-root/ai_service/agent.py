"""
AI agent logic: connects to the Product MCP Server, discovers its tools,
and runs the tool-calling loop against Groq to answer a question.

See README.md for the supported question types and the out-of-scope
handling strategy (both enforced through SYSTEM_PROMPT below).
"""

import json
import os

from dotenv import load_dotenv
from fastmcp import Client
from fastmcp.exceptions import ToolError
from groq import AsyncGroq

load_dotenv()

MCP_URL = os.environ.get("MCP_URL", "http://localhost:8000/mcp")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

# Safety net against a runaway tool-call loop, not expected to be hit in
# practice for the 4 supported question types.
MAX_TOOL_ROUNDS = 5

SYSTEM_PROMPT = """You are the HBntory inventory assistant.

You answer questions about products and stock using ONLY the tools
available to you. Never invent a product name, price, description, or
stock quantity. If a tool returns an error or the information isn't
available, say so clearly instead of guessing.

You only answer these 4 question types:
1. Product details (e.g. price, description of one product).
2. Where a product is available (which branch/branches have it in stock).
3. What products are available in one branch.
4. Whether a shopping list (several products with quantities) can be
   satisfied by one or more branches.

For any other kind of question, politely say you can only answer
questions about product details and stock availability, and don't call
any tool.

If you are looking for a product and only know its name, use the
search tool first to find its product_id, don't guess a category
filter.

If a search or lookup returns no results, state plainly that the
product or information was not found in the catalog. Do not suggest
contacting customer service, visiting a website, or any other channel
you have no information about.

Always reply in the same language the question was asked in.
"""


def _mcp_tool_to_groq_tool(tool) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.inputSchema,
        },
    }


def _tool_result_to_text(result) -> str:
    text_blocks = [block.text for block in result.content if hasattr(block, "text")]
    return "\n".join(text_blocks) if text_blocks else json.dumps(result.structured_content)


async def ask(question: str) -> str:
    """Answer one question end-to-end: discover tools, run the tool-calling
    loop against Groq, return the final text answer."""
    groq_client = AsyncGroq()

    async with Client(MCP_URL) as mcp_client:
        mcp_tools = await mcp_client.list_tools()
        tools = [_mcp_tool_to_groq_tool(tool) for tool in mcp_tools]

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]

        for _ in range(MAX_TOOL_ROUNDS):
            response = await groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                tools=tools,
            )
            message = response.choices[0].message

            if not message.tool_calls:
                return message.content

            messages.append(message.model_dump(exclude_none=True))

            for tool_call in message.tool_calls:
                args = json.loads(tool_call.function.arguments or "{}")
                print(f"[tool call] {tool_call.function.name}({args})")

                try:
                    result = await mcp_client.call_tool(tool_call.function.name, args)
                    content = _tool_result_to_text(result)
                except ToolError as exc:
                    content = f"Error: {exc}"

                print(f"[tool result] {content}")

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": content,
                    }
                )

        return (
            "I couldn't complete this request after several tool calls, "
            "please try rephrasing your question."
        )