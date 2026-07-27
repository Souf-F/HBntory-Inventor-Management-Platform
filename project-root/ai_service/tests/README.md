# Tests

## Why this exists

Groq's free tier gives a limited daily token quota, and its smaller
open-source models are less reliable at tool calling than a frontier
model (see architecture.md, Decision 7). Early on we iterated by
running `manual_test.py` end to end and reading the output by eye, but
that burns quota on every single run, even for a one-line code change,
and a fix for one question type can silently break another since they
all share the same SYSTEM_PROMPT.

This test suite splits verification into two halves so we can rerun
the cheap half constantly and save the expensive half for when it
actually matters.

## Files

**`fakes.py`**
Fake `AsyncGroq` and `fastmcp.Client` implementations. Not a test file
itself, just the building blocks the other files use to simulate
Groq/MCP responses (including errors) without any network call.

**`test_agent_unit.py`**
Tests `agent.py`'s own logic against the fakes above: does the retry
loop actually retry on a malformed generation, does it stop
immediately on a rate limit instead of wasting attempts, does a tool
error get reported back to the model instead of crashing, does the
loop bail out after `MAX_TOOL_ROUNDS`. Zero tokens spent, since Groq
and the MCP server are never actually called.

**`test_app_unit.py`**
Tests the Flask endpoint in `app.py`: input validation (missing
question, blank question, wrong type), and that a valid request calls
`agent.ask` and returns its result as JSON. `agent.ask` is patched out
here too, so this never touches Groq either.

**`test_agent_live.py`**
The real thing: the same 7 questions as `manual_test.py`, turned into
automatic assertions instead of output you read by eye (e.g. the price
question must contain "169.99", the shopping list question must name
"Paris"). This is what actually tells you whether the model itself
behaves correctly, which the mocked tests above cannot answer since
they never call the model. Marked `@pytest.mark.live` and excluded by
default (see pytest.ini) because every run costs real Groq quota.

## Running

```bash
pip install -r ../requirements-dev.txt

pytest              # test_agent_unit.py + test_app_unit.py only, free, run anytime
pytest -m live      # test_agent_live.py, real Groq/MCP calls, run sparingly
```

`pytest -m live` requires the Product API and the MCP server running
(see product_mcp_server/README.md), and `GROQ_API_KEY` set in `.env`.