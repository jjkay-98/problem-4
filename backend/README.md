# Backend API

The local server uses Python's standard library HTTP server and SQLite. It binds to [0m[0m\`127.0.0.1:8765\` and serves the frontend from [0m[0m\`web/index.html\`.

## Read routes

- [0m[0m\`GET /api/health\` — process health and simulated mode
- [0m[0m\`GET /api/bootstrap\` — initial data for all dashboard pages
- [0m[0m\`GET /api/dashboard\` — summary metrics and automation state
- [0m[0m\`GET /api/transactions\`
- [0m[0m\`GET /api/incidents\`
- [0m[0m\`GET /api/reconciliation\`
- [0m[0m\`GET /api/approvals\` — pending requests
- [0m[0m\`GET /api/policies\`
- [0m[0m\`GET /api/audit\`

## Demo actions

- [0m[0m\`POST /api/demo/simulate\` — create a synthetic stuck payment
- [0m[0m\`POST /api/transactions/{id}/enquiry\` with JSON [0m[0m\`{"outcome":"success|failure|unknown"}\`
- [0m[0m\`POST /api/approvals/{id}/decision\` with JSON [0m[0m\`{"decision":"approve|reject","actor":"Alex Morgan"}\`
- [0m[0m\`PUT /api/policies\` with JSON [0m[0m\`{"id":"fail_safe","enabled":true}\`
- [0m[0m\`POST /api/automation\` with JSON [0m[0m\`{"paused":true}\`

All actions are simulated and append an audit event. A confirmed failure may create a maker-checker request, but approval does not invoke a reversal or alter a ledger. This demo has no real authentication; the actor field is demonstration data only. Keep the server on loopback and never use real banking data.