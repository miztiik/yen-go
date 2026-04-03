# Architecture Compliance Rules

> This document defines the architectural constraints and dependency enforcement policies, adapted for the Yen-Go project.

---

## 1. Top-Level Layer Structure

Yen-Go enforces a strict distinction between frontend (Preact/Vite) and backend (Python data pipelines/adapters).

- `frontend/` - Must not read locally from `backend/` space during execution (communicates strictly via JSON/SGF assets).
- `backend/puzzle_manager/` - Must not generate UI or manipulate DOM; handles core parsing and NLP.
  - `core/` - Business logic, parsing models, internal typing.
  - `adapters/` - Downstream plugins that convert 3rd party formats into `core/` schemas.

## 2. Dependency Direction Rules

### Backend / Python Rule

| From        | To          | Allowed | Intent                                       |
| ----------- | ----------- | ------- | -------------------------------------------- |
| `adapters/` | `core/`     | ✅      | Adapters rely on core schemas                |
| `core/`     | `adapters/` | ❌      | Core must NEVER know about specific adapters |
| `core/`     | `core/`     | ✅      | Internal cohesion                            |

### Frontend / TypeScript Rule

| From          | To            | Allowed | Intent                           |
| ------------- | ------------- | ------- | -------------------------------- |
| `components/` | `services/`   | ✅      | UI interacts with business logic |
| `services/`   | `components/` | ❌      | Services must be view agnostic   |

---

## 3. Allowed/Forbidden Imports Enforcement

For any `core/` module:

- Do not import external API/scraping SDKs directly inside core parsers.
- Use the shared `HttpClient` wrapper instead of raw `requests` snippets.

### Exception Allowlist (If Applicable)

If exceptions must be made to architectural bounds:

- We track them via testing mechanisms / allowlists.
- Allowlists are **DELETE-ONLY**.
- Agents should not add new tech-debt/dependency exceptions. If one is required, it must be escalated to a "Level 5" correction level discussion.

---

## 4. Alternative Architectural Patterns

If tempted to breach isolation layers, prefer these patterns:

- **Dependency Injections / Callbacks**: Instead of Service calling Component, inject a callback handler to the Service.
- **Shared Schemas**: If an adapter needs to build SGFs, import `SgfBuilder` from `core`, rather than re-creating the builder logic in the adapter or referencing another adapter.
- **Events**: Use observable stores instead of tightly coupling state rendering.
