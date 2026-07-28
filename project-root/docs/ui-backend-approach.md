# HBntory — UI/Backend Approach

## 1. Two interfaces, two audiences, no shared state

The project deliberately exposes two separate frontends, served independently, sharing neither session nor rendering logic:

- **`admin/`** — authenticated Backoffice, restricted to employees and the admin
- **`client_web/`** — public site, no authentication, catalog + AI chat

This choice avoids a single interface carrying two different authorization logics (authenticated vs anonymous), which would have multiplied conditionals and the risk of showing the wrong button or data to the wrong person.

## 2. Frontend stack

Both frontends are written in vanilla HTML/CSS/JS, with a custom rendering engine (`support.js`, dc-runtime) that interprets an `<x-dc>` template: `{{ }}` bindings, `<sc-if>` conditionals, `<sc-for>` loops, state managed via a `Component extends DCLogic` class with `state`, `setState`, and `renderVals()` recomputing the values exposed to the template on every state change.

No build framework (React, Vue) on the frontend side: everything runs in a single `index.html` file per interface, loaded directly by the browser. This choice was made to keep local deployment simple as part of the project (no `npm install`, no bundler).

## 3. Backend: Flask REST API

The Backoffice (`backoffice/`) is a classic Flask REST API:
- Blueprints per domain (`auth_bp`, `stock_bp`, `users_bp`)
- SQLAlchemy for the ORM, SQLite as the development database
- Flask-Login for the session, bcrypt for password hashing
- flask-cors to allow cross-origin requests from frontends served on different ports

Every route returns structured JSON (`{"status": "success"/"error", ...}`), never HTML. The frontend only does `fetch()` with `credentials: 'include'` to pass the session cookie along.

## 4. Where the business logic lives

The rule applied throughout the project: **the frontend is only a display and input layer, never a decision layer**.

Concretely:
- The frontend can hide a "Create user" button for a common user, but that's only a display convenience — the `POST /users` route still refuses the request server-side if the role doesn't match
- Quantity validation (`quantity > 0`, integer) is redone server-side even though the frontend already validates the form
- The branch name shown in the UI (resolved from an ID) is a display convenience; the actual authorization always compares the connected account's branch ID to the requested resource's, never the name

This separation is documented in detail in `docs/authentication.md`.

## 5. Frontend/backend communication: REST, no state kept

Every interaction (login, stock management, user management, AI chat) goes through standard REST calls, no WebSocket. The AI chat in particular is stateless: each question sent to `POST /ask` is handled independently, with no conversation history kept server-side between two questions. This choice simplifies deployment (no persistent connection to manage) and fits the use case (one-off questions, no multi-turn dialogue needed).

## 6. Approach to network errors on the frontend

Every `fetch()` call goes through a centralized `api()` method that distinguishes three cases:
- Success (`res.ok`) → state update, confirmation toast
- Business error returned by the server (4xx with a JSON message) → display the exact error message returned by the backend, not a generic one
- Full network failure (server unreachable, timeout) → generic "Server not responding" message, distinct from the case above

This distinction proved useful during debugging: a bug that looked like a random disconnection turned out to be a page reload caused by the development tool (Live Server) rather than an actual session issue — the clear distinction between network error and business error in the logs made it possible to isolate quickly.

## 7. What isn't in the frontend

No product information (name, price, description) is hardcoded or cached on the frontend beyond the current display: every page reloads data from the external product API or the local stock database on every visit. See `docs/architecture.md`, section 3, for the golden rule on product/stock separation.