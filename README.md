# SHAAS Banking Transaction Resilience Demo

A local full-stack prototype of the self-healing banking transaction operations console. It demonstrates transaction monitoring, simulated status enquiries, reconciliation, maker-checker approvals, policy controls, and audit history.

## Run locally

Requires Python 3.9 or newer. The backend uses only the Python standard library.

```powershell
python backend/server.py
```

Open http://127.0.0.1:8765. The server binds to loopback locally and stores demo state in backend/data/shaas_demo.sqlite3.

## Deploy to Render

The repository includes a Render Blueprint at render.yaml. Connect the GitHub repository to Render, create a Blueprint from the repository, and deploy shaas-banking-demo. Render will assign the public onrender.com URL after the first successful deploy.

The free service may spin down when idle, and its local SQLite file is ephemeral. Demo state can reset after sleep or redeploy. Use only synthetic data.

## Safety boundary

This is a local/demo application only. Network responses are simulated. Approval records a decision but does not move funds, post a ledger entry, or submit a reversal. No banking rails, customer accounts, or production credentials are connected. Do not expose real banking data.

See backend/README.md for API endpoints.