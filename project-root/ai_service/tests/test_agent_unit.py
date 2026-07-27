"""
Mocked tests for agent.py: no network calls, no Groq tokens consumed.

These test our own code (the tool-calling loop, retries, error
handling) against fake Groq/MCP clients, not the real model's
reliability. Safe to run as often as you want. For real-model behavior,
see test_agent_live.py (uses real quota, run sparingly).
"""

import json

import pytest
from fastmcp.exceptions import ToolError

import agent
from tests.fakes import (
    FakeGroqClient,
    FakeMCPClient,
    FakeTool,
    FakeToolCall,
    FakeToolResult,
    make_api_error,
    make_rate_limit_error,
    make_response,
)


def _install_fakes(monkeypatch, groq_script, tools, tool_results):
    fake_groq = FakeGroqClient(groq_script)
    fake_mcp = FakeMCPClient(tools, tool_results)
    monkeypatch.setattr(agent, "AsyncGroq", lambda: fake_groq)
    monkeypatch.setattr(agent, "Client", lambda url: fake_mcp)
    return fake_groq, fake_mcp


def test_mcp_tool_to_groq_tool_conversion():
    tool = FakeTool("get_product_details", "Get product details", {"type": "object"})
    converted = agent._mcp_tool_to_groq_tool(tool)
    assert converted == {
        "type": "function",
        "function": {
            "name": "get_product_details",
            "description": "Get product details",
            "parameters": {"type": "object"},
        },
    }


def test_tool_result_to_text_uses_text_blocks():
    result = FakeToolResult('{"product_id": "X"}')
    assert agent._tool_result_to_text(result) == '{"product_id": "X"}'


@pytest.mark.asyncio
async def test_ask_returns_direct_answer_without_tool_calls(monkeypatch):
    _install_fakes(
        monkeypatch,
        groq_script=[make_response(content="I can only help with products and stock.")],
        tools=[],
        tool_results={},
    )

    answer = await agent.ask("Tell me a joke.")

    assert answer == "I can only help with products and stock."


@pytest.mark.asyncio
async def test_ask_calls_a_tool_and_returns_final_answer(monkeypatch):
    fake_call = FakeToolCall("call_1", "get_product_details", json.dumps({"product_id": "HB-MON-2102"}))

    fake_groq, fake_mcp = _install_fakes(
        monkeypatch,
        groq_script=[
            make_response(tool_calls=[fake_call]),
            make_response(content="It costs 169.99."),
        ],
        tools=[FakeTool("get_product_details")],
        tool_results={"get_product_details": FakeToolResult('{"price": 169.99}')},
    )

    answer = await agent.ask("What's the price of the monitor?")

    assert answer == "It costs 169.99."
    assert fake_mcp.calls == [("get_product_details", {"product_id": "HB-MON-2102"})]


@pytest.mark.asyncio
async def test_ask_reports_tool_error_back_to_the_model(monkeypatch):
    fake_call = FakeToolCall("call_1", "get_product_details", json.dumps({"product_id": "unknown"}))

    fake_groq, fake_mcp = _install_fakes(
        monkeypatch,
        groq_script=[
            make_response(tool_calls=[fake_call]),
            make_response(content="That product was not found."),
        ],
        tools=[FakeTool("get_product_details")],
        tool_results={"get_product_details": ToolError("No product found with product_id 'unknown'.")},
    )

    answer = await agent.ask("What's the price of unknown?")

    assert answer == "That product was not found."
    # The error, not fabricated data, must have been fed back as the tool result.
    second_call_messages = fake_groq.calls[1]["messages"]
    tool_message = next(m for m in second_call_messages if m["role"] == "tool")
    assert "No product found" in tool_message["content"]


@pytest.mark.asyncio
async def test_ask_retries_on_malformed_generation_then_succeeds(monkeypatch):
    fake_groq, _ = _install_fakes(
        monkeypatch,
        groq_script=[make_api_error(), make_response(content="Recovered.")],
        tools=[],
        tool_results={},
    )

    answer = await agent.ask("What's the price of the monitor?")

    assert answer == "Recovered."
    assert len(fake_groq.calls) == 2


@pytest.mark.asyncio
async def test_ask_gives_up_after_max_retries(monkeypatch):
    fake_groq, _ = _install_fakes(
        monkeypatch,
        groq_script=[make_api_error() for _ in range(agent.MAX_API_RETRIES)],
        tools=[],
        tool_results={},
    )

    answer = await agent.ask("What's the price of the monitor?")

    assert "technical problem" in answer
    assert len(fake_groq.calls) == agent.MAX_API_RETRIES


@pytest.mark.asyncio
async def test_ask_returns_immediately_on_rate_limit_without_retrying(monkeypatch):
    fake_groq, _ = _install_fakes(
        monkeypatch,
        groq_script=[make_rate_limit_error()],
        tools=[],
        tool_results={},
    )

    answer = await agent.ask("What's the price of the monitor?")

    assert "rate limit" in answer.lower()
    assert len(fake_groq.calls) == 1


@pytest.mark.asyncio
async def test_ask_stops_after_max_tool_rounds(monkeypatch):
    fake_call = FakeToolCall("call_1", "get_product_details", json.dumps({"product_id": "X"}))
    # The model never stops calling tools: one tool-call response per round.
    script = [make_response(tool_calls=[fake_call]) for _ in range(agent.MAX_TOOL_ROUNDS)]

    _install_fakes(
        monkeypatch,
        groq_script=script,
        tools=[FakeTool("get_product_details")],
        tool_results={"get_product_details": FakeToolResult('{"price": 1}')},
    )

    answer = await agent.ask("What's the price of the monitor?")

    assert "couldn't complete this request" in answer