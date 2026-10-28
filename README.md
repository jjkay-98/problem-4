# SHAAS Banking Transaction Demo

A banking transaction resilience demo with a multi-page dashboard, a Python API for local use, and a static Vercel deployment mode.

## Deploy to Vercel

[Deploy this repository to Vercel](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fjjkay-98%2Fproblem-4)

1. Sign in to Vercel and grant access to `jjkay-98/problem-4` if prompted.
2. Keep the **Root Directory** at the repository root (`./`).
3. Leave the Framework Preset as **Other** and leave the Build Command blank. `vercel.json` serves the `web` folder.
4. Deploy. Vercel will provide the public `*.vercel.app` address.

The hosted site runs in browser demo mode. It saves simulated changes in that browser's local storage; those changes are device-specific and clear when site data is removed. The Python/SQLite backend is for local demos and is not deployed to Vercel, since serverless local files are not durable.

## Run the full local backend

Requires Python 3.9 or newer; no third-party packages are needed.

```powershell
python backend/server.py
```

Open http://127.0.0.1:8765. The API stores state in `backend/data/shaas_demo.sqlite3`.

## Demo scope

All transactions, network status enquiries, approvals, and healing actions are simulated. Approval records a decision but does not send a reversal, post a ledger entry, or move funds. This prototype has no production authentication, banking integration, or compliance certification. Do not use real customer data.
