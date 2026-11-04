# PayPal Tradesman

PayPal AI Hackathon entry. A tradesperson talks through a job in their own language; Claude drafts a priced, itemized estimate in the customer's language; PayPal invoices handle the deposit, change orders, and final payment.

- **Deadline:** submissions close Nov 12, 2026. One summary lists 1:30 AM IST Nov 13 = **2:00 PM Central Nov 12**. Confirm on Devpost; plan to submit that morning.
- **Hackathon rule that matters most:** the project must *meaningfully* use both PayPal and AI. Judged on technical implementation, design, impact, innovation, presentation.
- **Submission needs:** public repo with open-source license (MIT, done), public YouTube demo under 3 minutes, English description, working demo or setup instructions.
- **Plan and progress:** @docs/MILESTONES.md. Check off tasks there as they're finished.

## Stack

- `backend/`: Python 3.12, FastAPI, SQLModel (SQLite locally, Postgres in prod), httpx, `anthropic` SDK. Deployed on Render (`render.yaml`) at `api.alexanderk.dev`.
- `frontend/`: React 18 + Vite + Tailwind 3 + `vite-plugin-pwa`. Deployed as a Cloudflare Worker with static assets (`frontend/wrangler.jsonc`) at `tradesman.alexanderk.dev`.
- AI: Claude Sonnet 5.5 (`claude-sonnet-5-5`) for estimates, translation, change orders, receipts; Claude Haiku 5.5 (`claude-haiku-5-5`) for text-to-SQL, hours parsing, digests. Whisper on Cloudflare Workers AI for speech-to-text (Claude doesn't take audio).
- Payments: PayPal Invoicing API v2, **sandbox only**.

## Commands

```bash
# backend (from backend/, with .venv active)
uvicorn app.main:app --reload          # API on :8000, creates + seeds SQLite on first run
python -m pytest -q                    # no keys or network needed
python -m scripts.paypal_smoke <buyer> # real sandbox invoice end to end (needs .env)

# frontend (from frontend/)
npm run dev                            # :5173
npm run typecheck && npm run build     # what CI runs
```

CI (`.github/workflows/ci.yml`) runs pytest, typecheck, and build on every push. Keep it green.

## Where things live

- `backend/app/services/claude.py`: every Claude call. Each call forces one tool with a JSON schema (`_call_tool`), so responses are always structured.
- `backend/app/services/paypal.py`: PayPal client (OAuth, invoices, reminders, webhook verification).
- `backend/app/services/stt.py`: speech-to-text, swappable.
- `backend/app/routers/`: `jobs.py` (jobs, walkthrough, line items, send), `money.py` (summary, ask, receipts), `webhooks.py`.
- `backend/app/models.py`: all tables. `totals.py`: all money math.
- `frontend/src/api.ts`: every API call and shared types. `i18n.tsx`: all UI strings in `es` and `en`.

## Rules (do not break these)

1. **Money is integer cents** everywhere in the backend. Convert to dollars only at the PayPal boundary (`cents_to_str`) and in the UI (`dollars()`).
2. **Prices come only from the price book.** Claude picks a `price_book_item_id`; `apply_price_book` sets the price. Anything unmatched is `needs_price` and blocks sending. Never let a model-supplied number become a price.
3. **No invented measurements.** Quantities come from what the tradesperson said; photos are context only. Missing info becomes a question.
4. **A person confirms before money moves or a customer sees anything:** send estimate, approve change order, confirm receipt split, send final invoice.
5. **AI-written SQL** goes through `guard_sql` and runs on `readonly_engine`. Never execute model SQL any other way.
6. **Secrets only in backend env vars.** Nothing secret in `frontend/` (everything there ships to the browser). Never commit `.env`.
7. **Tests never hit the network.** Mock Claude and PayPal like `tests/test_core.py` does. Add a test for any new money math or guardrail.
8. **Every UI string goes in `i18n.tsx`** in both `es` and `en`. Customer-facing text comes from Claude in the customer's language, not from `i18n.tsx`.
9. Record important actions in `AuditLog` (sends, approvals, payments, edits).

## UI conventions

The look borrows from a paper work-order pad. Tokens are in `frontend/tailwind.config.js`:

- `concrete` page background, `paper` white slips with `rule` lines between rows (`.slip`, `.slip-row`).
- `tape` yellow is used **only** for the record button and the single main action on a screen. Don't spread it.
- `flag` red marks things needing attention; `carbon` blue for secondary actions and links; `ok` green for paid.
- Barlow for text, Barlow Semi Condensed + tabular figures (`.figures`) for numbers and headings.
- Mobile-first: big tap targets (≥ 48 px), voice before typing, sentence case, no all-caps labels.

## Working style

- Work one milestone task at a time from `docs/MILESTONES.md`; run tests, typecheck, and build before calling it done; then tick the box.
- Prefer small commits with clear messages.
- Ask before changing the data model in a way that drops or renames columns (there's no migration tool yet; recreate the local SQLite DB when tables change).
