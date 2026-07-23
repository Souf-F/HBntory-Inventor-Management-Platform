# AI Query Service

Independent service that receives a natural-language question from the
Client Web Interface and answers it using the Product MCP Server tools.
Never invents data: if the information isn't available through the tools,
it says so clearly.

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
