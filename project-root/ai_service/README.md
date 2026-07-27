# AI Query Service

Independent service that receives a natural-language question from the
Client Web Interface and answers it using the Product MCP Server tools.
Never invents data: if the information isn't available through the tools,
it says so clearly.

## Endpoint

REST, not WebSockets (see architecture.md, Decision 1): each question
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

| # | Type | Example (French) | Example (English) |
|---|------|-------------------|--------------------|
| 1 | Product details | "Quel est le prix de la Huile de tournesol 5L ?" | "What's the price of the 5L sunflower oil?" |
| 2 | Where a product is available | "Où puis-je trouver du café en grains 1kg ?" | "Which branches have 1kg coffee beans in stock?" |
| 3 | What's available in one branch | "Qu'est-ce qui est en stock dans la branche de Lyon ?" | "What products are in stock at the Lyon branch?" |
| 4 | Shopping list feasibility | "J'ai besoin de 3 sacs de riz et 2 bidons d'huile, quelle branche peut satisfaire ça ?" | "I need 3 bags of rice and 2 jugs of oil, which branch can cover that?" |

The agent answers in whichever language the question was asked in
(English or French); no separate configuration is needed for this, it's
native LLM behavior.

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
  product_mcp_server/README.md): they never fabricate a result, they
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
deliberate trade-off from Decision 7 (architecture.md): a free
provider's smaller open-source models are less reliable at tool
calling than a frontier model, mitigated by keeping the tool set small
and retrying on failure.
