# SHAAS Banking Transaction Resilience Demo

A local full-stack prototype of the self-healing banking transaction operations console. It demonstrates transaction monitoring, simulated status enquiries, reconciliation, maker-checker approvals, policy controls, and audit history.

## Run locally

Requires Python 3.9 or newer. The backend uses only the Python standard library.

```powershell
python backend/server.py
```

Open <http://127.0.0.1:8765>. The server binds to loopback and stores demo state in `backend/data/shaas_demo.sqlite3`.

## Safety boundary

This is a local demo only. Network responses are simulated. Approval records a decision but does not move funds, post a ledger entry, or submit a reversal. No banking rails, customer accounts, or production credentials are connected. Do not expose this server to a network or use real customer data.

See [backend API documentation](backend/README.md) for endpoints.