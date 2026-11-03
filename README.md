# PayPal Tradesman

PayPal AI Hackathon entry by Alexander Kashyap.

A tradesperson talks through a job in their own language. Claude turns it into a priced, itemized estimate in the customer's language, and the job's money runs through PayPal: deposit, change orders, final invoice.

- **App:** React PWA (installable from the browser) at `tradesman.alexanderk.dev`
- **API:** FastAPI at `api.alexanderk.dev`
- **AI:** Claude Sonnet 5.5 (estimates, translation, receipts) and Claude Haiku 5.5 (money questions)
- **Payments:** PayPal Invoicing API (sandbox)

## Repo layout

```
backend/           FastAPI API
  app/services/    claude.py, paypal.py, stt.py (speech-to-text)
  app/routers/     jobs, money + receipts, PayPal webhooks
  app/seed.py      demo tradesperson + price book (runs on first start)
  scripts/         paypal_smoke.py: day-1 sandbox invoice check
  tests/           runs without network (Claude and PayPal mocked)
frontend/          React + Vite + Tailwind PWA
render.yaml        Render blueprint for the API
```

## Run it locally

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in keys (see below)
uvicorn app.main:app --reload
python -m pytest -q         # tests need no keys
```

**Frontend**

```bash
cd frontend
npm install
cp .env.example .env        # VITE_API_URL=http://localhost:8000
npm run dev                 # http://localhost:5173
```

To try it on your phone over the local network, run `npm run dev -- --host` and open the address it prints. The microphone needs HTTPS on phones, so for real recording use the deployed URL or a tunnel.

## Keys you need

| Key | Where to get it |
| --- | --- |
| `ANTHROPIC_API_KEY` | console.anthropic.com |
| `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET` | developer.paypal.com, Apps & Credentials, **Sandbox** |
| `PAYPAL_WEBHOOK_ID` | Your sandbox app, Webhooks, add `https://api.alexanderk.dev/api/webhooks/paypal` with event `INVOICING.INVOICE.PAID` |
| `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_AI_TOKEN` | Cloudflare dashboard, Workers AI (token with Workers AI permission). Optional: without it, typed notes still work. |
| `DATABASE_URL` | Supabase or Neon Postgres connection string (SQLite is fine locally) |

Keys live only in the backend's environment. Nothing secret goes in the frontend.

## Day-1 checklist (Nov 3–4)

1. Create sandbox accounts at developer.paypal.com: one business (you), one personal (the customer).
2. Fill `backend/.env`, then run `python -m scripts.paypal_smoke <sandbox-buyer-email>` and pay the invoice as the buyer at sandbox.paypal.com.
3. Deploy the API on Render (New, Blueprint, this repo) and point `api.alexanderk.dev` at it in Cloudflare DNS.
4. Add the PayPal webhook (table above) and pay a test invoice: the job should flip to "deposit paid".
5. Deploy the app: `cd frontend && npm run deploy` (or connect the repo in Cloudflare with root directory `frontend`). Set `VITE_API_URL=https://api.alexanderk.dev` at build time.

## Guardrails built in

- **Prices come only from the price book.** Claude picks items by id; the backend looks up the price. Anything unmatched is marked "needs price" and blocks sending.
- **No invented measurements.** The prompt forbids estimating sizes from photos; missing dimensions become questions.
- **Read-only money questions.** AI-written SQL must be a single SELECT, gets a row limit, and runs on a read-only database role in production.
- **Webhooks are verified** with PayPal before an invoice is marked paid.

## What's next (see the TODOs in code)

- Nov 8: change orders with customer approval, time logging, receipt split confirmation
- Nov 9: final invoice (fixed vs. time and materials), demo seed data
- Nov 10: dashboard cards (real hourly rate, profit per job), weekly digest
- Customer-facing page via signed link; object storage for photos; sign-in
