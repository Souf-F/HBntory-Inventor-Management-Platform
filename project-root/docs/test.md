# HBntory — UI/Backend Approach

## 1. Two interfaces, two audiences, no shared state

The project deliberately exposes two separate frontends, served independently, sharing neither session nor rendering logic:

- **`admin/`** — authenticated Backoffice, restricted to employees and the admin
- **`client_web/`** — public site, no authentication, catalog + AI chat

This choice avoids a single interface carrying two different authorization logics (authenticated vs anonymous), which would have multiplied conditionals and the risk of showing the wrong button or data to the wrong person.

## 2. Frontend stack

Both frontends are written in vanilla HTML/CSS/JS, with a custom rendering engine (`support.js`, dc-runtime) that interprets an `<x-dc>` template: `{{ }}` bindings, `<sc-if>` conditionals, `<sc-for>` loops, state managed via a `Component extends DCLogic` class with `state`, `setState`, and `renderVals()` recomputing the values exposed to the template on every state change.

No build framework (React, Vue) on the frontend side: everything runs in a single `index.html` file per interface, loaded directly by the browser. This choice was made to keep local deployment simple as part of the project (no `npm install`, no bundler).