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
from groq import APIError, AsyncGroq, RateLimitError

load_dotenv()

MCP_URL = os.environ.get("MCP_URL", "http://localhost:8000/mcp")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

# Safety net against a runaway tool-call loop, not expected to be hit in
# practice for the 4 supported question types.
MAX_TOOL_ROUNDS = 5

# Groq's free Llama models occasionally emit a malformed tool call (as
# plain text instead of a structured tool_calls entry), which the API
# rejects with a 400. This is stochastic: retrying the same request often
# succeeds on the next sample. Not a sign the request itself is invalid.
MAX_API_RETRIES = 3

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

To find where a product is available (question type 2), call
check_stock with only its product_id, no branch_name: it already
checks every branch at once. Only use list_branch_stock, and only pass
a branch_name to check_stock, when the user has explicitly named a
branch in their question. Never guess or invent a branch name: there
is no tool to list branch names, so if a branch you were given doesn't
exist, say so, don't try other guessed names.

Whenever a question involves a quantity (e.g. "I need 5 of X", question
type 4), always use check_shopping_list with that product_id and
quantity, even for a single product. check_stock only tells you
whether a product exists in a branch at all, it cannot tell you if a
specific quantity is available, never use it for quantity questions.

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
            response = None
            last_error = None
            for attempt in range(MAX_API_RETRIES):
                try:
                    response = await groq_client.chat.completions.create(
                        model=GROQ_MODEL,
                        messages=messages,
                        tools=tools,
                        # One tool call at a time: the model must wait for a
                        # real result before it can use it as an argument to
                        # the next call, instead of guessing a placeholder.
                        parallel_tool_calls=False,
                    )
                    break
                except RateLimitError as exc:
                    print(f"[groq rate limit] {exc}")
                    return (
                        "Sorry, the assistant is temporarily unavailable "
                        "(rate limit reached). Please try again later."
                    )
                except APIError as exc:
                    last_error = exc
                    print(f"[groq error, attempt {attempt + 1}] {exc}")

            if response is None:
                print(f"[groq error] giving up after {MAX_API_RETRIES} attempts: {last_error}")
                return (
                    "Sorry, I ran into a technical problem while processing "
                    "your question. Please try again."
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