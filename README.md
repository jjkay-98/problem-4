# SHAAS Banking Transaction Resilience Demo

A local full-stack prototype of the self-healing banking transaction operations console. It demonstrates transaction monitoring, simulated status enquiries, reconciliation, maker-checker approvals, policy controls, and audit history.

## Deploy the demo

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2Fjjkay-98%2Fproblem-4)

Render will ask you to sign in, grant access to this private GitHub repository if needed, review the Blueprint, and approve deployment. Render supplies the app's public URL after the first deploy succeeds.

The Blueprint uses Render's free web-service plan. Free services can sleep when idle and their local SQLite state is ephemeral, so demo changes may reset after sleep or redeploy. Use only synthetic data.

## Run locally

Requires Python 3.9 or newer. The backend uses only the Python standard library.

```powershell
python backend/server.py
```

Open http://127.0.0.1:8765. The server binds to loopback locally and stores demo state in backend/data/shaas_demo.sqlite3.

## Safety boundary

This is a local/demo application only. Network responses are simulated. Approval records a decision but does not move funds, post a ledger entry, or submit a reversal. No banking rails, customer accounts, or production credentials are connected. Do not expose real banking data.

See backend/README.md for API endpoints.