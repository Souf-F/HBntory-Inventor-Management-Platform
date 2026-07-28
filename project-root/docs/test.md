# HBntory — Tests and Fixed Vulnerabilities

Each team member documents here the tests they performed on their part of the project, and the vulnerabilities/bugs identified and fixed. One test = one line. One vulnerability = one line with the corresponding fix.

---

## Soufiane Filali — Auth, security, stock operations, Backoffice

### Functional tests

- [x] Login with valid credentials (admin) → session created, `role` and `branch_id` returned
- [x] Login with valid credentials (common_user) → session created, redirected to stock view
- [x] Login with incorrect password → 401, generic message
- [x] Login with disabled account (`is_active = False`) → 401, cannot log in
- [x] Logout → session invalidated
- [x] Admin: list users
- [x] Admin: create a user (common_user, tied to a branch)
- [x] Admin: change a user's branch
- [x] Admin: change a user's password
- [x] Admin: deactivate an account (soft-delete)
- [x] Admin: reactivate a deactivated account
- [x] Common user: add stock to their branch
- [x] Common user: remove stock from their branch
- [x] Common user: check the stock of one product in their branch
- [x] Common user: list all stock in their branch
- [x] Admin: global stock overview across all branches (read-only)

### Security tests

- [x] SQL injection on the `username`/`password` login fields
- [x] IDOR: a common user attempts to access another branch's stock by editing the URL (`branch_id`) → 403
- [x] Mass assignment: attempt to inject `role` or `is_active` into a user-creation request body
- [x] Type confusion: `quantity` sent as a string or float instead of an int → rejected (400)
- [x] Session after deactivation: an account disabled while it has an active session loses access on the next request
- [x] An admin attempts to call a stock route (`POST /branches/<id>/stock`) → 403 (wrong role)
- [x] A common user attempts to call a users route (`GET /users`) → 403 (wrong role)

### Vulnerabilities found and fixed

- [x] `branch_id` missing from the `/login` response → frontend received `undefined`, breaking routing to the stock view and subsequent stock calls (URL `/branches/undefined/stock`). Fixed in `routes/auth.py`.
- [x] `PRODUCT_API_URL` pointed to a non-existent Docker URL (`http://external-products-api:5000`) → every product validation failed silently, producing a false "Unknown product_id" message. Fixed in `app/config.py`.
- [x] `PATCH /users/<id>/reactivate` route missing while the frontend called it → added, protected by `role_required(Role.ADMIN)`.
- [x] Database still containing old branch names ("Metro Paris Nord") out of sync with the code → caused every branch-name lookup to fail on the AI agent side. Fixed by resetting the database (`rm hbntory.db` + `python -m app.seed`).

---

## Sagal-Louise Haider — DB, SQLAlchemy models, Product API integration, admin interface (Claude Design)

### Functional tests

- []
- []
- []

### Security tests

- []
- []

### Vulnerabilities found and fixed

- []
- []

---

## Noham Oulma — Product MCP Server, AI Query Service

### Functional tests

- [x] `list_products` — paginated listing from the external product API
- [x] `search_products` — free-text search by name, used by the agent to find a `product_id` instead of guessing a `category` filter
- [x] `get_product_details` — details of a valid product
- [x] `get_product_details` — invalid identifier → clear error (no crash)
- [x] `check_stock` — across all branches
- [x] `check_stock` — restricted to one named branch
- [x] `check_stock` — nonexistent branch name → clear error, no attempt to guess another name
- [x] `list_branch_stock` — stock listing for one branch
- [x] `check_shopping_list` — list satisfiable by at least one branch
- [x] `check_shopping_list` — list not satisfiable anywhere
- [x] `POST /ask` — valid question → 200, `{"answer": ...}`
- [x] `POST /ask` — missing/blank/non-string `question` field → 400, clear error, no call to the agent
- [x] `GET /health` — 200, `{"status": "ok"}`
- [x] Public chat: out-of-scope question (not about product, stock, or branch) → polite refusal, no tool called
- [x] Public chat: question with a quantity → correctly uses `check_shopping_list`, never `check_stock` alone
- [x] Public chat: the 4 core question types rephrased differently → same correct grounded answer, not tied to exact wording
- [x] Public chat: product that exists in the catalog but has no stock row anywhere → clearly reported as unavailable, not confused with "product doesn't exist"
- [x] Public chat: shopping list quantity too large for any single branch → clearly reported as not satisfiable
- [x] 14 mocked unit tests (`ai_service/tests/test_agent_unit.py`, `test_app_unit.py`) covering the retry loop, rate-limit short-circuit, tool-error reporting, and the `MAX_TOOL_ROUNDS` safety net, against fake Groq/MCP clients (no quota spent)

### Security tests

- [x] Product API down during a call → clear error message, no MCP server crash
- [x] Automatic retry on transient Groq API error (up to `MAX_API_RETRIES`)
- [x] Groq rate limit reached → clear user-facing message, no raw technical error leaked

### Vulnerabilities found and fixed

- [x] `check_stock` with `branch_name` consistently failed (`No branch found with name 'HBntory Paris'`) even though the branch name provided was correct → actual cause: local database not resynced with the new branch names (see Soufiane's section). Not a bug in `tools/stock.py`.
- [x] With parallel tool calls enabled, the model sometimes called a second tool using an invented placeholder argument (e.g. `product_id: "awaiting_search_result"`) for a value it didn't have yet, instead of waiting for the first tool's real result. Fixed in `agent.py` with `parallel_tool_calls=False`, forcing one tool call at a time.
- [x] `AsyncGroq()` was created in `agent.ask()` but never closed, leaking an HTTP connection on every request (visible as `RuntimeError: Event loop is closed` during test teardown). Fixed by using `async with AsyncGroq() as groq_client`.

---

## General notes

- Any checked box ` [x]` should include a brief note if the test revealed unexpected behavior, even a minor one.
- A "found and fixed" vulnerability entry should always specify: the observed symptom, the actual root cause identified, and the file that was fixed.
- This file is a living document: update it as you go, not just before a defense/presentation.