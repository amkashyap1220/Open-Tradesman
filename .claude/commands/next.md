---
description: Pick up the next unchecked task from docs/MILESTONES.md and build it
---

1. Read `docs/MILESTONES.md`. Find the first unchecked task in the earliest unfinished milestone. If $ARGUMENTS names a task or milestone, use that instead.
2. Say which task you picked and give a short plan: files to change, any new tests, and anything I need to do by hand (keys, dashboards, deploys). If the task is mine to do by hand (accounts, DNS, deploys), walk me through it step by step instead of writing code.
3. Build it following the rules in `CLAUDE.md`.
4. Run `python -m pytest -q` in `backend/` and `npm run typecheck && npm run build` in `frontend/` for whichever side you touched. Fix failures.
5. Tick the task in `docs/MILESTONES.md` and tell me what to try to see it working.
