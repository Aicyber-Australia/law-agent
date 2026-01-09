# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AusLaw AI - An Australian Legal Assistant MVP that validates "White Box" citation logic and "Lawyer Matching" workflow using Supabase and CopilotKit.

## Architecture

```
Frontend (Next.js)  →  /api/copilotkit  →  FastAPI Backend  →  Supabase
     ↓                      ↓                    ↓
CopilotSidebar      HttpAgent proxy      LangGraph Agent
                                         (lookup_law, find_lawyer tools)
```

**Frontend**: Next.js 14 + React 18 + CopilotKit + Tailwind CSS
**Backend**: FastAPI + LangGraph + langchain-openai (GPT-4o)
**Database**: Supabase PostgreSQL with full-text search (tsvector)

## Development Commands

### Backend (requires conda environment `law_agent`)
```bash
cd backend
conda activate law_agent
python main.py                    # Start server on localhost:8000
python test_db.py                 # Test Supabase connection and data
```

### Frontend
```bash
cd frontend
npm install                       # Install dependencies
npm run dev                       # Start dev server on localhost:3000
npm run build                     # Production build
npm run lint                      # ESLint check
```

### Database
Run `database/setup.sql` in Supabase SQL Editor to create tables and mock data.

## Environment Variables

Backend requires `.env` file in `/backend`:
```
SUPABASE_URL=
SUPABASE_KEY=
OPENAI_API_KEY=
```

## Key Files

- `backend/main.py` - FastAPI app, LangGraph agent definition, Supabase tools
- `frontend/app/api/copilotkit/route.ts` - Proxy endpoint connecting frontend to backend
- `frontend/app/layout.tsx` - CopilotKit provider with agent configuration
- `frontend/app/page.tsx` - Main UI with document viewer and chat sidebar
- `database/setup.sql` - Database schema and mock data

## Agent Configuration

The LangGraph agent uses:
- `MemorySaver` checkpointer for state management
- System prompt enforcing tool usage and citation format
- Two tools: `lookup_law` (full-text search) and `find_lawyer` (filter by location/specialty)

## Full-Text Search

The `lookup_law` tool converts queries to PostgreSQL tsquery format using OR logic:
```
"rent increase" → "rent | increase"
```
This ensures broader matches in the MVP's limited dataset.
