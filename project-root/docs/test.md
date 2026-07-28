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

- [x] Login with valid credentials (admin and common_user) → session created
- [x] Login with an incorrect password → 401, generic message
- [x] `GET /branches` → correct branch names returned
- [x] `DELETE /users/<id>` → account deactivated, row and stock history kept
- [x] `PATCH /users/<id>/reactivate` → account reactivated, login works again
- [x] `PATCH /users/<id>` with a new username → change persisted (was silently ignored before, see below)
- [x] `health_check()` against the real Product API → reachable
- [x] `get_product()` against the real Product API → product returned by SKU
- [x] `list_products()` against the real Product API → full catalog returned (39 products)
- [x] Stock page displays product names resolved from the external catalog, in a single API call per page
- [x] Product API stopped → stock page still loads, names fall back to raw SKUs, no crash
- [x] Admin page: `Statut` and `Branche` columns display correctly for every user

### Security tests

- [x] `employee1` (branch 1) sends `POST /branches/2/stock` by hand with curl, bypassing the interface → 403 Branch not allowed
- [x] Account deactivated **from the admin interface** while the target's session is active → target's session invalidated on their next request, not at next login (`user_loader` checks `is_active`). Tested with two browser windows; complements Soufiane's server-side test of the same rule.
- [x] Logout → `POST /logout` actually reaches the server and destroys the session (was frontend-only before, see below)
- [x] `POST /login` with an empty or malformed JSON body → 401, no 500 and no stack trace exposed
- [x] Admin account targeted by `DELETE /users/1` with curl → 403, the single admin cannot lock the system out
- [x] Schema review: no product name, price, description or metadata stored locally — `stock` holds only `branch_id`, `product_id` (SKU) and `quantity`

### Vulnerabilities found and fixed

- [x] Logout only cleared the frontend state → the session cookie stayed valid server-side, so a saved request still worked after "logging out". Fixed in `admin/index.html` (calls `POST /logout`).
- [x] `user_loader` did not check `is_active` → an account deactivated mid-session kept full access until the user logged out on their own. Fixed in `app/__init__.py`.
- [x] The admin account could be modified or soft-deleted through the API → since no endpoint creates another admin, this locked the system out irreversibly and required reseeding. The interface hid the action but the backend allowed it. Fixed in `routes/users.py` (403 on any admin-targeted write).
- [x] `POST /login` with a missing field raised `AttributeError` on `None.encode()` → 500 with a stack trace instead of a clean rejection. Fixed in `routes/auth.py` (`get_json(silent=True)` + explicit field check).
- [x] `add_stock` returned "Unknown product_id" (404) when the Product API was simply unreachable → misleading message, employee unable to diagnose. Cause: `get_product()` swallows every `ProductAPIError` and returns `None`, making an outage indistinguishable from an unknown SKU. Fixed in `routes/stock.py` (503 on outage, 404 only on a real not-found).
- [x] SQLite does not enforce declared `FOREIGN KEY` constraints by default → a stock or user row could reference a nonexistent branch, silently. Fixed in `app/models.py` with a SQLAlchemy engine listener running `PRAGMA foreign_keys=ON` on every connection.
- [x] Product name resolution made one HTTP call per SKU → a 20-row stock page triggered 20 round-trips to the external API. Fixed in `app/product_api.py` with `get_product_names()`, a single catalog call mapped to the SKUs on screen.
- [x] Product API client (Backoffice/admin side) used the wrong port and read the wrong JSON key when parsing the catalog (`results`, not `products`) → every product lookup from the Backoffice returned nothing. Fixed in `app/product_api.py`.
- [x] Admin page read `u.status` while the backend returns `u.is_active` → `Statut` and `Branche` columns always rendered empty. Fixed in `admin/index.html`.
- [x] Admin page `reactivate()` called the wrong route → reactivation silently failed. Fixed in `admin/index.html`.

> **Note on overlapping entries.** Soufiane's `PRODUCT_API_URL` entry and the Product API
> client entry above are two distinct defects on the same integration: his on the Docker URL
> used for stock validation, this one on the port and response parsing used by the Backoffice
> product lookup. Likewise, the branch-isolation and mid-session-deactivation rules appear in
> both sections because each was verified from a different angle, server-side by Soufiane,
> through the admin interface here.

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