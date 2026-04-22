# AusLaw AI

Next.js 14 · FastAPI · CopilotKit (LangGraph) · Supabase (Postgres, pgvector, Storage).

**Requirements:** Node 18+, Python 3.11+.

## Local

**Backend** (`backend/`):

```bash
python -m venv .venv && .venv\Scripts\activate   # Windows
# source .venv/bin/activate                        # macOS / Linux
pip install -r requirements.txt
cp .env.example .env                               # Windows: copy .env.example .env
python main.py
```

**Frontend** (`frontend/`):

```bash
npm install
# .env.local — see below
npm run dev
```

- http://localhost:3000  
- Chat: `/chat` — CopilotKit works without a session; REST (`/api/v1/...`), uploads, PDFs, and `/account` expect a logged-in user.

## Environment

| Path | Notes |
|------|--------|
| `backend/.env` | `SUPABASE_URL`, `SUPABASE_KEY` (service role), `SUPABASE_JWT_SECRET`, `OPENAI_API_KEY`; optional `COHERE_API_KEY`, `REDIS_URL`, `LANGGRAPH_DB_URL`, `CORS_ORIGINS`, `DOCUMENTS_BUCKET`, `BRIEF_PDF_BUCKET`, `RETENTION_DAYS`, `ALLOWED_DOCUMENT_HOSTS`, `SENTRY_DSN` |
| `frontend/.env.local` | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_BACKEND_URL`, `BACKEND_URL` (server-side proxy target); optional `NEXT_PUBLIC_SITE_URL` |

## Database

Apply SQL under `supabase/migrations/` in Supabase (start with `20260306110000_production_foundation.sql`).

Optional: run `database/migration_rag.sql` and `database/migration_insurance_claim.sql` in the SQL editor when you need legislation RAG tables or insurance-claim action templates (after core migrations).

## Production (frontend)

```bash
cd frontend && npm run build && npm run start
```

## Scripts (optional)

- `backend/scripts/ingest_corpus.py` — RAG ingest  
- `backend/scripts/run_retention.py` — retention  

## License

MIT
