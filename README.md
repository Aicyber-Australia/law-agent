# AusLaw AI

An Australian Legal Assistant that provides state-specific legal information, lawyer matching, and step-by-step checklists for legal procedures.

## Features

- **Legal Research**: Search Australian legislation with proper citations
- **Lawyer Matching**: Find lawyers by specialty and location
- **Procedure Checklists**: Generate step-by-step guides for legal processes (e.g., getting bond back, breaking a lease)
- **State-Aware**: All information is tailored to the user's Australian state/territory

## Tech Stack

- **Frontend**: Next.js 14, CopilotKit, Tailwind CSS
- **Backend**: FastAPI, LangGraph, GPT-4o
- **Database**: Supabase (PostgreSQL with full-text search)

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+ with conda
- Supabase account

### Setup

1. **Clone and install**
   ```bash
   git clone <repo-url>
   cd law_agent

   # Frontend
   cd frontend && npm install

   # Backend
   cd ../backend
   conda create -n law_agent python=3.11
   conda activate law_agent
   pip install -r requirements.txt
   ```

2. **Environment variables**

   Create `backend/.env`:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   OPENAI_API_KEY=your_openai_key
   ```

3. **Database setup**

   Run `database/setup.sql` and `database/migration_v2.sql` in Supabase SQL Editor.

4. **Run**
   ```bash
   # Terminal 1 - Backend
   cd backend && conda activate law_agent && python main.py

   # Terminal 2 - Frontend
   cd frontend && npm run dev
   ```

5. Open http://localhost:3000

## Architecture

```
Frontend (Next.js)  →  /api/copilotkit  →  FastAPI Backend  →  Supabase
     ↓                      ↓                    ↓
CopilotSidebar      HttpAgent proxy      LangGraph Agent
+ StateSelector                          with 3 tools
```

## License

MIT
