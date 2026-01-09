# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AusLaw AI - An Australian Legal Assistant MVP with two planned branches:
- **Research Branch**: RAG-based legal Q&A with citations (current)
- **Action Branch**: Interactive checklists for legal procedures (planned)

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
```

### Frontend
```bash
cd frontend
npm install
npm run dev                       # Start dev server on localhost:3000
npm run build
npm run lint
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

## Backend Structure

```
backend/
├── main.py                 # FastAPI app, LangGraph agent, CopilotKit integration
├── app/
│   ├── config.py           # Environment variables, logging setup
│   ├── db/
│   │   └── supabase_client.py   # Supabase connection singleton
│   └── tools/
│       ├── lookup_law.py   # Full-text search in legal_docs table
│       └── find_lawyer.py  # Filter lawyers by location/specialty
```

## Agent Configuration

The LangGraph agent in `main.py`:
- Uses `create_react_agent` with `MemorySaver` checkpointer
- System prompt enforces tool usage and citation format: `"According to [Act Name] [Section]..."`
- Integrates with CopilotKit via `LangGraphAGUIAgent` at `/copilotkit` endpoint

## Database Schema

**legal_docs**: `id`, `content`, `metadata` (JSONB with source/section/url), `search_vector` (auto-generated tsvector)

**lawyers**: `id`, `name`, `specialty`, `location`, `rate`

## Full-Text Search

The `lookup_law` tool converts queries to PostgreSQL tsquery with OR logic:
```
"rent increase" → "rent | increase"
```
