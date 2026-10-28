# Backend API

The local server uses Python's standard library HTTP server and SQLite. It binds to 127.0.0.1:8765 and serves the frontend from web/index.html.

## Read routes

- GET /api/health — process health and simulated mode
- GET /api/bootstrap — initial data for all dashboard pages
- GET /api/dashboard — summary metrics and automation state
- GET /api/transactions
- GET /api/incidents
- GET /api/reconciliation
- GET /api/approvals — pending requests
- GET /api/policies
- GET /api/audit

## Demo actions

- POST /api/demo/simulate — create a synthetic stuck payment
- POST /api/transactions/{id}/enquiry with JSON body: {"outcome":"success|failure|unknown"}
- POST /api/approvals/{id}/decision with JSON body: {"decision":"approve|reject","actor":"Alex Morgan"}
- PUT /api/policies with JSON body: {"id":"fail_safe","enabled":true}
- POST /api/automation with JSON body: {"paused":true}

All actions are simulated and append an audit event. A confirmed failure may create a maker-checker request, but approval does not invoke a reversal or alter a ledger. This demo has no real authentication; the actor field is demonstration data only. Keep the server on loopback and never use real banking data.