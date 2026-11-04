# Milestones

Build window: Nov 3 to Nov 12, 2026. Core build ends Nov 10; Nov 11–12 are for the demo and submission. Tick boxes as tasks are done. Each milestone ends with "Done when", which is the check that it really works.

**If behind, cut in this order:** weekly digest, AI job summary, estimate-accuracy suggestions. **Never cut:** bilingual estimate, deposit invoice, change orders, the demo video.

## M0 · Scaffold (Nov 3) ✅

- [x] FastAPI backend: models, Claude / PayPal / speech-to-text services, jobs + money + webhook routes, demo seed
- [x] React PWA: bottom nav, walkthrough recorder, work-order estimate view, money page, settings
- [x] Tests with mocked Claude and PayPal; CI on GitHub
- [x] MIT license

## M1 · Accounts, keys, deploys (Nov 3–4)

- [ ] PayPal sandbox: one business account (tradesperson), one personal account (customer)
- [ ] `backend/.env` filled; `python -m scripts.paypal_smoke <buyer>` creates an invoice and the buyer pays it at sandbox.paypal.com
- [ ] Anthropic API key working: create a job locally, type notes in Spanish, get a drafted estimate
- [ ] Postgres on Supabase or Neon; `DATABASE_URL` set on Render
- [ ] API deployed on Render; `api.alexanderk.dev` CNAME in Cloudflare DNS
- [ ] App deployed to `tradesman.alexanderk.dev` with `VITE_API_URL=https://api.alexanderk.dev`
- [ ] PayPal webhook registered for `INVOICING.INVOICE.PAID` to `/api/webhooks/paypal`; `PAYPAL_WEBHOOK_ID` set
- [ ] Confirm the Devpost deadline time and rules on naming

**Done when:** on a phone, from the home-screen icon, you send an estimate, pay the deposit as the sandbox buyer, and the job flips to "Deposit paid" without touching anything.

## M2 · Estimate quality (Nov 5–6)

- [ ] Cloudflare Workers AI token set; voice notes transcribe from iPhone (mp4) and Android/Chrome (webm). Fix the model name or format handling in `stt.py` if needed
- [ ] Three realistic Spanish test walkthroughs (bathroom repaint, drywall patch, faucet swap) produce sensible estimates; tune `ESTIMATE_SYSTEM`
- [ ] Trade glossary in the prompt (mud, skim coat, drop cloth, trim) so terms translate correctly
- [ ] Answering the AI's questions updates the estimate (already wired via "Update estimate"; verify it)
- [ ] Line items editable: quantity and text, not just price
- [ ] Photos stored in object storage instead of local `uploads/` (Render's disk is wiped on redeploy)

**Done when:** a 20-second Spanish voice note produces an English estimate you'd be comfortable sending, with no invented prices.

## M3 · Customer page and deposit (Nov 7)

- [ ] Customer page at `/c/<signed-token>`: no login, customer's language, "show original" toggle
- [ ] Customer approves the estimate; approval goes in `AuditLog`
- [ ] Pay button opens the PayPal invoice (`payer_url`)
- [ ] Check whether a customer can pay a sandbox invoice by card without a PayPal account; note the answer in the README

**Done when:** the customer flow works end to end on a second phone.

## M4 · Change orders and job costs (Nov 8)

- [ ] Change order: photo + voice note → Claude drafts a priced change order (price-book guardrail applies)
- [ ] Customer approves the change order on their page *before* work continues
- [ ] Receipts screen: snap a receipt, confirm or fix the job split, mark personal items
- [ ] Log hours by voice ("me and my helper, 6 hours") parsed with Haiku into `TimeEntry` rows

**Done when:** water-damage change order goes from photo to customer approval in under a minute.

## M5 · Final invoice and demo data (Nov 9)

- [ ] Final invoice: fixed price = quoted total + approved change orders − deposit; time and materials = hours × rate + receipts × (1 + markup) − deposit
- [ ] Tests for both final-invoice formulas
- [ ] Job marked "Paid" via webhook on the final invoice
- [ ] Seed script: about 3 months of realistic jobs, invoices, receipts, and hours so the dashboard has data
- [ ] AI job summary for the customer (cut-able)

**Done when:** a full job runs estimate → deposit → change order → final → paid, all in sandbox.

## M6 · Money dashboard (Nov 10)

- [ ] Cards: who owes me (exists), coming in, real hourly rate, profit per job, materials spend
- [ ] Ask box answers in Spanish from real ledger numbers (verify `guard_sql` holds with real questions)
- [ ] Read-only Postgres role for `DATABASE_URL_READONLY`
- [ ] Weekly digest (cut-able): one message with owed, overdue, and this week's hourly rate

**Done when:** "¿Cuánto me deben este mes?" returns the right number from seeded data.

## M7 · Ship (Nov 11–12)

- [ ] Polish pass on phone: loading states, error messages, empty states
- [ ] Spanish speaker recorded for the demo voice notes
- [ ] Demo video under 3 minutes, uploaded to YouTube as public (script in the project doc)
- [ ] Devpost write-up: problem, how PayPal and Claude are used, guardrails, future work, one quote from a real tradesperson if possible
- [ ] Sandbox buyer login in the submission notes so judges can pay a test invoice
- [ ] Submit by the morning of Nov 12
