# GraphGuard — Admin/Operational Layer Intake

## Status

Waiting on the existing GraphGuard source code. Chosen stack: **FastAPI + SQLAlchemy/Alembic + React**.

## What to upload

Drop the project into this workspace so that `/home/user` contains the repo root, e.g.:

```
/home/user/
├── backend/            (or: api/, server/, app/)
│   ├── app/
│   │   ├── main.py
│   │   ├── models/
│   │   ├── api/  or  routers/
│   │   └── services/  or  ai/  ml/
│   ├── alembic/
│   └── requirements.txt  |  pyproject.toml
└── frontend/           (or: web/, client/, ui/)
    ├── package.json
    └── src/
```

Upload the **source only** — no `node_modules/`, `.venv/`, `__pycache__/`, `dist/`,
`build/`, or large model/data artifacts (`.pt`, `.pkl`, `.parquet`, `.csv` datasets).
Those are skipped automatically if present, but they slow the transfer and the scan.

If a full upload is impractical, the highest-value subset in priority order:

1. **ORM models / schema** — everything defining `Account`, `Transaction`, `Alert`
2. **API routers** — every file with `@router.get/post/...`
3. **AI pipeline** — GraphSAGE, XGBoost, EWS rules, graph construction, risk fusion
4. **DB config + Alembic versions dir**
5. **Frontend route definitions + the API client module** (page components optional)

## What happens next

1. Run the discovery script:
   `python3 _gg_agent/inspect_codebase.py /home/user -o _gg_agent/CODEBASE_MAP.md -j _gg_agent/CODEBASE_MAP.json`
2. Produce a **written integration plan** for your sign-off before any code is written:
   - exact new tables + FK edges onto existing models
   - new vs. modified endpoints (with backward-compatibility notes)
   - the auth/RBAC middleware insertion point
   - how config changes reach the live pipeline without a restart
   - where each existing UI screen gets wired to real data (no UI redesign)
   - migration strategy (additive Alembic revision, never destructive)
   - test plan
3. Implement in phases, one feature area at a time, with tests.

## Constraints that will be honoured

- No UI redesign, no new UI, no parallel frontend, no mock-only screens.
- Existing GraphSAGE / XGBoost / EWS / NetworkX / fusion code is **not rewritten** —
  the administrative layer is built around it.
- Backward compatibility of existing endpoints; additive Alembic migrations only.
- Every protected endpoint authorized; every significant action audited.
