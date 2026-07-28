# AI Query Service

Independent service that receives a natural-language question from the
Client Web Interface and answers it using the Product MCP Server tools.
Never invents data: if the information isn't available through the tools,
it says so clearly.

## Running

```bash
cd ai_service
pip install -r requirements.txt
python app.py
```

Reads `GROQ_API_KEY` and `MCP_URL` from `.env` (see `.env.example`).
Listens on `AI_SERVICE_PORT` (defaults to `8100`).

## Endpoint

REST, not WebSockets (see `architecture.md`, Decision 1): each question
is handled independently, no conversation history, so there's no need
for a persistent connection.

`POST /ask`
```json
{"question": "Quel est le prix du 24 inch Compact Monitor ?"}
```
```json
{"answer": "Le prix du 24 inch Compact Monitor est 169.99."}
```

`GET /health` for a basic liveness check.

## Supported question types

The assistant answers 4 types of questions about the product catalog and
branch stock. Any other question is politely declined, without calling
any tool.

| # | Type | Example |
|---|------|---------|
| 1 | Product details | "Give me the details of product HB-MON-2102" / "Quel est le prix de la Huile de tournesol 5L ?" |
| 2 | Where a product is available | "Where can I find the 24 inch Compact Monitor?" / "Où puis-je trouver du café en grains 1kg ?" |
| 3 | What's available in one branch | "What products are available at HBntory Paris?" / "Qu'est-ce qui est en stock dans la branche de Lyon ?" |
| 4 | Shopping list feasibility (multiple products with quantities) | "I need 3 units of 8-Port Managed Switch and 2 of Barcode Scanner USB, which branch(es) can supply all of it?" |

The agent answers in whichever language the question was asked in
(English or French); no separate configuration is needed for this, it's
native LLM behavior.

Branch names must match an existing branch exactly (`HBntory Paris`,
`HBntory Lyon`, `HBntory Marseille`). The agent has no fuzzy matching and
will say so if an unknown branch name is given, rather than guessing the
closest one.

## Out of scope questions

Handled directly by the system prompt: the agent is instructed to only
answer the 4 question types above, using the MCP tools, and to clearly
say it cannot help otherwise (e.g. "raconte-moi une blague", "quelle est
la météo ?"). No separate classification step: one LLM call decides both
whether the question fits and how to answer it. This keeps the
implementation simple, matching the project's two-week scope, at the
cost of being slightly less predictable than a dedicated classifier if
the model misjudges an edge-case question.

## Grounded responses (task 4)

The agent never invents a product name, price, description, stock
quantity, or branch. Every fact in an answer comes from a Product MCP
Server tool call, never from the model's own knowledge. This is
enforced in two places:

- The system prompt explicitly forbids inventing data, and requires the
  agent to say plainly when something wasn't found (no product, no
  branch, no stock), instead of suggesting an unfounded fallback like
  "contact customer service".
- The MCP tools themselves only return real data (see
  `product_mcp_server.md`): they never fabricate a result, they
  either return real values or a clear error (`ToolError`) that the
  agent reports back to the user.

Context is kept minimal on purpose: each tool only returns the fields
the agent actually needs (e.g. product_id, name, price, not every
internal field the Product API exposes), so the agent's context never
contains more internal data than necessary to answer.

### Known limitation: Groq tool-calling reliability

Groq's free Llama models occasionally emit a malformed tool call (as
plain text instead of a structured call) and briefly try to call two
tools at once with an invented placeholder argument for the one that
depends on the other's result. Both are mitigated, not fully
eliminated:

- `parallel_tool_calls=False` forces the agent to make one tool call
  at a time, so it can never use a placeholder for a result it hasn't
  received yet.
- A malformed generation is retried automatically (`MAX_API_RETRIES`
  in agent.py), since it's a stochastic sampling issue, not a sign the
  request itself was invalid: the same call often succeeds on retry.

If every retry fails, or the Groq free tier's daily token quota is
reached, the agent returns a clear "technical problem, try again"
message instead of crashing or guessing an answer. This is a
deliberate trade-off from Decision 7 (`architecture.md`): a free
provider's smaller open-source models are less reliable at tool
calling than a frontier model, mitigated by keeping the tool set small
and retrying on failure.

## Testing

See `ai_service/tests/README.md`: mocked unit tests (free, run anytime
with `pytest`) plus live tests against the real Groq/MCP stack (`pytest
-m live`, consumes quota, run sparingly).