# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AusLaw AI - An Australian Legal Assistant MVP that provides legal information, lawyer matching, and step-by-step checklists for legal procedures across Australian states/territories.

## Architecture

```
Frontend (Next.js)  →  /api/copilotkit  →  FastAPI Backend  →  Supabase
     ↓                      ↓                    ↓
CopilotSidebar      HttpAgent proxy      Custom LangGraph
+ StateSelector                          (CopilotKitState)
+ useCopilotReadable                          ↓
                                    Tools: lookup_law, find_lawyer,
                                           generate_checklist
```

**Frontend**: Next.js 14 + CopilotKit + Tailwind CSS
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
npm run dev                       # Start dev server on localhost:3000
npm run build
npm run lint
```

### Database
Run SQL files in Supabase SQL Editor:
- `database/setup.sql` - Initial schema and mock data
- `database/migration_v2.sql` - Adds action_templates table and state column

## Environment Variables

Backend `.env` file in `/backend`:
```
SUPABASE_URL=
SUPABASE_KEY=
OPENAI_API_KEY=
```

## Key Architecture Decisions

### CopilotKit Context Passing
The agent uses a **custom StateGraph** (not `create_react_agent`) to properly read frontend context:
- Frontend uses `useCopilotReadable` to share user's selected state
- Backend inherits from `CopilotKitState` and reads `state["copilotkit"]["context"]`
- Context items are Pydantic-like objects (use `item.description`, not `item.get("description")`)

### State-Based Legal Information
Australian law varies by state. The `StateSelector` component lets users pick their state (VIC, NSW, QLD, etc.), which is passed to all tool calls automatically.

## Backend Structure

```
backend/
├── main.py                 # FastAPI app, custom LangGraph, CopilotKit integration
├── app/
│   ├── config.py           # Environment variables, logging
│   ├── db/supabase_client.py
│   └── tools/
│       ├── lookup_law.py       # Full-text search in legal_docs
│       ├── find_lawyer.py      # Filter by location/specialty
│       └── generate_checklist.py  # LLM-generated or template-based checklists
```

Note: `app/agents/` directory exists but is not currently used. The main.py contains a simpler single-agent architecture.

## Database Schema

**legal_docs**: `id`, `content`, `metadata` (JSONB), `state`, `search_vector` (tsvector)

**lawyers**: `id`, `name`, `specialty`, `location`, `rate`

**action_templates**: `id`, `state`, `category`, `title`, `keywords` (array), `steps` (JSONB)

## Full-Text Search

The `lookup_law` tool converts queries to PostgreSQL tsquery with OR logic:
```
"rent increase" → "rent | increase"
```

## Code Style

- All comments and documentation must be in English
- After completing code changes, generate a commit message summarizing the changes

---

## Planned Feature: Document Upload & Analysis

Add capability to upload and analyze legal documents (leases, contracts, visa docs).

### Why No Sub-graph Needed
- Simple single tool flow: upload → parse → analyze
- No complex multi-step state management
- GPT-4o Vision handles images directly

### Implementation Steps

**1. Frontend - Enable file upload**
```tsx
// frontend/app/page.tsx
<CopilotSidebar
  imageUploadsEnabled={true}
  inputFileAccept=".pdf,.png,.jpg,.jpeg,.doc,.docx"
  ...
/>
```

**2. Backend - Install dependencies**
```bash
pip install pypdf python-docx pillow
```

**3. Create document parser**
```
backend/app/utils/document_parser.py
- parse_pdf(content: bytes) -> str
- parse_docx(content: bytes) -> str
- parse_image_to_base64(content: bytes) -> str
```

**4. Create analyze_document tool**
```
backend/app/tools/analyze_document.py
@tool
def analyze_document(document_text: str, analysis_type: str) -> str
    # analysis_type: "lease", "contract", "visa", "general"
```

**5. Update chat_node in main.py**
- Detect file attachments in messages
- Parse PDF/Word content
- Pass to agent as context

**6. Update system prompt**
Add document analysis instructions to BASE_SYSTEM_PROMPT
