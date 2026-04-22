# Repo notes (internal)

## Stack

- Frontend: `frontend/` — Next 14, CopilotKit, Tailwind, Supabase client. Chat UI: `app/chat/[conversationId]/ChatPageClient.tsx`. Copilot proxy: `app/api/copilotkit/route.ts`.
- Backend: `backend/` — FastAPI entry `main.py`, LangGraph in `app/agents/`, tools in `app/tools/`.
- Schema: `supabase/migrations/*.sql` only.

## Commands

```bash
cd backend && pip install -r requirements.txt && python main.py
cd frontend && npm install && npm run dev
```

Backend tests: `cd backend && pytest` (see `backend/tests/`).

## Auth behaviour (high level)

- `/chat` is usable without login (guest CopilotKit). `/account` and REST APIs that call `backendRequest` in the client still expect a session where enforced server-side.
- Backend `CopilotKitMiddleware`: JWT when present; optional user for guests (rate limit, no DB writes for guest paths — unchanged server rules).

## Env

Mirror `backend/.env.example` and `frontend/.env.local` (see root `README.md`).

## Styling

- Chat shell / Copilot overrides: `frontend/app/globals.css`.
- Mode theming: `document.documentElement` `data-mode` from `frontend/app/contexts/ModeContext.tsx`.

## Code style

Comments and user-facing copy in English unless product requires otherwise.
