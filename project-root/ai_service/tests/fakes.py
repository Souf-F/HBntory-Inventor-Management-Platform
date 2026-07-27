"""
Fake Groq/MCP clients for the mocked unit tests (tests/test_agent_unit.py).

No network calls, no tokens consumed: these stand in for AsyncGroq and
fastmcp.Client so we can test agent.py's own logic (the tool-calling
loop, retries, error handling) in isolation from the real, flaky, quota
limited services.
"""

import httpx
from groq import APIError, RateLimitError


def make_api_error(code="tool_use_failed"):
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    return APIError(f"mock error ({code})", request, body={"error": {"code": code}})


def make_rate_limit_error():
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(429, request=request, json={"error": {"code": "rate_limit_exceeded"}})
    return RateLimitError("mock rate limit", response=response, body={"error": {"code": "rate_limit_exceeded"}})


class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls

    def model_dump(self, exclude_none=True):
        data = {"role": "assistant", "content": self.content, "tool_calls": self.tool_calls}
        return {k: v for k, v in data.items() if not (exclude_none and v is None)}


class FakeToolCall:
    def __init__(self, id, name, arguments):
        self.id = id
        self.function = FakeFunctionCall(name, arguments)


class FakeFunctionCall:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class FakeChoice:
    def __init__(self, message):
        self.message = message


class FakeResponse:
    def __init__(self, message):
        self.choices = [FakeChoice(message)]


def make_response(content=None, tool_calls=None):
    return FakeResponse(FakeMessage(content=content, tool_calls=tool_calls))


class FakeGroqClient:
    """Replaces AsyncGroq(). `script` is a list of responses or exceptions,
    consumed one per call to chat.completions.create."""

    def __init__(self, script):
        self._script = list(script)
        self.calls = []
        self.chat = _FakeChat(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False


class _FakeChat:
    def __init__(self, client):
        self.completions = _FakeCompletions(client)


class _FakeCompletions:
    def __init__(self, client):
        self._client = client

    async def create(self, **kwargs):
        self._client.calls.append(kwargs)
        item = self._client._script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class FakeMCPClient:
    """Replaces fastmcp.Client(). `tools` is the list returned by
    list_tools(). `tool_results` maps a tool name to either its result
    object or an exception to raise when called."""

    def __init__(self, tools, tool_results):
        self._tools = tools
        self._tool_results = tool_results
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def list_tools(self):
        return self._tools

    async def call_tool(self, name, args):
        self.calls.append((name, args))
        result = self._tool_results[name]
        if isinstance(result, Exception):
            raise result
        return result


class FakeTool:
    def __init__(self, name, description="", input_schema=None):
        self.name = name
        self.description = description
        self.inputSchema = input_schema or {"type": "object", "properties": {}}


class FakeToolResult:
    def __init__(self, text):
        self.content = [FakeTextBlock(text)]
        self.structured_content = None


class FakeTextBlock:
    def __init__(self, text):
        self.text = text
