import os
import uuid
from contextlib import asynccontextmanager
from typing import Any, Literal, Optional

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Request,
    Response,
    Depends,
    Query,
    Form,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from langchain_openai import ChatOpenAI
from copilotkit import LangGraphAGUIAgent
from ag_ui_langgraph import add_langgraph_fastapi_endpoint

from app.agents.conversational_graph import (
    get_conversational_graph,
    initialize_conversational_graph,
    shutdown_conversational_graph,
)
from app.auth import get_current_user, get_optional_user
from app.config import (
    logger,
    CORS_ORIGINS,
    SENTRY_DSN,
    DOCUMENTS_BUCKET,
    BRIEF_PDF_BUCKET,
)
from app.db import supabase
from app.db.production_store import (
    add_message,
    create_conversation,
    create_signed_download_url,
    get_brief,
    get_conversation,
    get_document,
    list_conversations,
    record_audit_event,
    soft_delete_conversation,
    update_brief_pdf_path,
    update_conversation,
    upload_brief_pdf_and_get_url,
    upload_document_and_create_record,
)
from app.security.rate_limit import rate_limiter
from app.services.pdf_renderer import render_brief_pdf
from app.utils.document_parser import parse_document

# Security: File upload size limit (10MB)
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024

# Default signed URL expiry
SIGNED_URL_EXPIRY_SECONDS = 60 * 60 * 6  # 6h


if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[FastApiIntegration()],
            traces_sample_rate=0.1,
        )
        logger.info("Sentry integration enabled")
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to initialize Sentry (%s)", exc)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Validate configuration on startup."""
    # Validate Supabase connection
    try:
        supabase.table("legislation_documents").select("id").limit(1).execute()
        logger.info("Supabase connection validated")
    except Exception as e:
        logger.error("Supabase connection failed: %s", e)
        raise SystemExit(1)

    # Validate OpenAI API key by making a minimal request
    try:
        test_model = ChatOpenAI(model="gpt-4o", temperature=0, max_tokens=5)
        test_model.invoke("test")
        logger.info("OpenAI API key validated")
    except Exception as e:
        logger.error("OpenAI API key validation failed: %s", e)
        raise SystemExit(1)

    await initialize_conversational_graph()
    agent.graph = get_conversational_graph()

    logger.info("AusLaw AI backend started successfully")
    yield
    await shutdown_conversational_graph()
    logger.info("AusLaw AI backend shutting down")


app = FastAPI(
    title="AusLaw AI API",
    description="Australian Legal Assistant Backend",
    version="2.0.0",
    lifespan=lifespan,
)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a correlation ID to every request/response."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# Combined auth + rate limiting middleware for /copilotkit endpoint
class CopilotKitMiddleware(BaseHTTPMiddleware):
    """Apply auth validation and distributed rate limiting to /copilotkit."""

    RATE_LIMIT = 30  # requests per minute
    WINDOW = 60  # seconds

    async def dispatch(self, request: Request, call_next):
        # Only apply to /copilotkit POST requests
        if request.url.path == "/copilotkit" and request.method == "POST":
            # Auth check: validate Bearer token
            user = await get_optional_user(request)
            if not user:
                return Response(
                    content='{"detail": "Authentication required"}',
                    status_code=401,
                    media_type="application/json",
                )

            client_host = request.client.host if request.client else "unknown"
            user_identifier = user.get("user_id") or client_host
            allowed = rate_limiter.allow(
                scope="copilotkit",
                identifier=user_identifier,
                limit=self.RATE_LIMIT,
                window_seconds=self.WINDOW,
            )
            if not allowed:
                logger.warning("Rate limit exceeded for /copilotkit")
                return Response(
                    content='{"detail": "Rate limit exceeded. Please try again later."}',
                    status_code=429,
                    media_type="application/json",
                )

        return await call_next(request)


# Add middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(CopilotKitMiddleware)

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
)

agent_description = (
    "Australian Legal Assistant - natural conversational help with "
    "legal questions, rights information, lawyer referrals, and optional deep analysis"
)
logger.info("Using CONVERSATIONAL graph with optional deep analysis")

agent = LangGraphAGUIAgent(
    name="auslaw_agent",
    description=agent_description,
    graph=get_conversational_graph(),
)

# Integrate with CopilotKit (using LangGraphAGUIAgent)
add_langgraph_fastapi_endpoint(
    app=app,
    agent=agent,
    path="/copilotkit",
)


# ============================================
# Request/Response Models
# ============================================


class ConversationCreateRequest(BaseModel):
    conversation_id: Optional[str] = None
    title: str = "New Conversation"
    ui_mode: Literal["chat", "analysis"] = "chat"
    legal_topic: str = "general"
    user_state: Optional[str] = None


class ConversationUpdateRequest(BaseModel):
    title: Optional[str] = None
    status: Optional[Literal["active", "archived", "deleted"]] = None
    ui_mode: Optional[Literal["chat", "analysis"]] = None
    legal_topic: Optional[str] = None
    user_state: Optional[str] = None


class MessageCreateRequest(BaseModel):
    role: Literal["user", "assistant", "system", "tool"]
    content: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BriefPDFResponse(BaseModel):
    brief_id: str
    conversation_id: str
    version: int
    download_url: str
    expires_in: int


# ============================================
# Utility
# ============================================


def _enforce_rate_limit(scope: str, identifier: str, limit: int, window_seconds: int) -> None:
    if not rate_limiter.allow(scope=scope, identifier=identifier, limit=limit, window_seconds=window_seconds):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")


# ============================================
# Basic endpoints
# ============================================


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# ============================================
# Conversation APIs
# ============================================


@app.post("/api/v1/conversations")
def create_conversation_endpoint(
    payload: ConversationCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    _enforce_rate_limit("create_conversation", user_id, limit=30, window_seconds=60)

    try:
        conversation = create_conversation(
            user_id=user_id,
            conversation_id=payload.conversation_id,
            title=payload.title,
            ui_mode=payload.ui_mode,
            legal_topic=payload.legal_topic,
            user_state=payload.user_state,
        )
    except Exception as exc:
        logger.error("Failed to create conversation for user %s: %s", user_id, exc)
        raise HTTPException(status_code=409, detail="Unable to create conversation")

    record_audit_event(
        user_id=user_id,
        conversation_id=conversation["id"],
        event_type="conversation.created",
        event_payload={"title": conversation.get("title")},
    )

    return {
        "conversation_id": conversation["id"],
        "thread_id": conversation["id"],
        "title": conversation.get("title"),
        "created_at": conversation.get("created_at"),
    }


@app.get("/api/v1/conversations")
def list_conversations_endpoint(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    conversations = list_conversations(user_id=user_id, limit=limit, offset=offset)
    return {
        "items": conversations,
        "limit": limit,
        "offset": offset,
    }


@app.get("/api/v1/conversations/{conversation_id}")
def get_conversation_endpoint(
    conversation_id: str,
    message_limit: int = Query(default=100, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    conversation = get_conversation(user_id=user_id, conversation_id=conversation_id, message_limit=message_limit)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.patch("/api/v1/conversations/{conversation_id}")
def update_conversation_endpoint(
    conversation_id: str,
    payload: ConversationUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    updated = update_conversation(
        user_id=user_id,
        conversation_id=conversation_id,
        **payload.model_dump(exclude_none=True),
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Conversation not found")

    record_audit_event(
        user_id=user_id,
        conversation_id=conversation_id,
        event_type="conversation.updated",
        event_payload=payload.model_dump(exclude_none=True),
    )
    return updated


@app.delete("/api/v1/conversations/{conversation_id}")
def delete_conversation_endpoint(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    deleted = soft_delete_conversation(user_id=user_id, conversation_id=conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")

    record_audit_event(
        user_id=user_id,
        conversation_id=conversation_id,
        event_type="conversation.deleted",
        event_payload={},
    )
    return {"deleted": True}


@app.post("/api/v1/conversations/{conversation_id}/messages")
def create_conversation_message_endpoint(
    conversation_id: str,
    payload: MessageCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]

    conversation = get_conversation(user_id=user_id, conversation_id=conversation_id, message_limit=1)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    message = add_message(
        user_id=user_id,
        conversation_id=conversation_id,
        role=payload.role,
        content=payload.content,
        metadata=payload.metadata,
    )

    record_audit_event(
        user_id=user_id,
        conversation_id=conversation_id,
        event_type="message.created",
        event_payload={"message_id": message["id"], "role": payload.role},
    )

    return message


# ============================================
# Document APIs
# ============================================


@app.post("/api/v1/documents/upload")
async def upload_document_endpoint(
    request: Request,
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Form(default=None),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    _enforce_rate_limit("upload_document", user_id, limit=10, window_seconds=60)

    allowed_extensions = {".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg", ".gif", ".webp"}
    filename = file.filename or "unknown"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(allowed_extensions)}",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB",
        )

    parsed_text: Optional[str] = None
    parsing_status = "parsed"
    try:
        parsed_text, _ = parse_document(content, filename)
    except Exception:
        parsing_status = "failed"

    try:
        if conversation_id:
            create_conversation(
                user_id=user_id,
                conversation_id=conversation_id,
                title="New Conversation",
            )

        document = upload_document_and_create_record(
            user_id=user_id,
            original_filename=filename,
            mime_type=file.content_type or "application/octet-stream",
            content=content,
            conversation_id=conversation_id,
            parsed_text=parsed_text,
            parsing_status=parsing_status,
        )

        signed_url = create_signed_download_url(
            bucket=DOCUMENTS_BUCKET,
            storage_path=document["storage_path"],
            expires_in=SIGNED_URL_EXPIRY_SECONDS,
        )

        return {
            "document_id": document["id"],
            "conversation_id": document.get("conversation_id"),
            "filename": document["original_filename"],
            "mime_type": document.get("mime_type"),
            "file_size_bytes": document.get("file_size_bytes"),
            "parsing_status": document.get("parsing_status"),
            "document_url": signed_url,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Document upload failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to upload document")


@app.get("/api/v1/documents/{document_id}/signed-url")
def get_document_signed_url_endpoint(
    document_id: str,
    expires_in: int = Query(default=SIGNED_URL_EXPIRY_SECONDS, ge=60, le=86400),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    document = get_document(user_id=user_id, document_id=document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    signed_url = create_signed_download_url(
        bucket=DOCUMENTS_BUCKET,
        storage_path=document["storage_path"],
        expires_in=expires_in,
    )
    return {
        "document_id": document_id,
        "document_url": signed_url,
        "expires_in": expires_in,
    }


# ============================================
# Brief APIs
# ============================================


@app.get("/api/v1/briefs/{brief_id}")
def get_brief_endpoint(
    brief_id: str,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    brief = get_brief(user_id=user_id, brief_id=brief_id)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")
    return brief


@app.post("/api/v1/briefs/{brief_id}/pdf", response_model=BriefPDFResponse)
def generate_brief_pdf_endpoint(
    brief_id: str,
    expires_in: int = Query(default=900, ge=60, le=86400),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    brief = get_brief(user_id=user_id, brief_id=brief_id)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")

    if brief.get("pdf_storage_path"):
        signed_url = create_signed_download_url(
            bucket=BRIEF_PDF_BUCKET,
            storage_path=brief["pdf_storage_path"],
            expires_in=expires_in,
        )
        return BriefPDFResponse(
            brief_id=brief["id"],
            conversation_id=brief["conversation_id"],
            version=brief["version"],
            download_url=signed_url,
            expires_in=expires_in,
        )

    markdown_content = brief.get("markdown_content") or ""
    if not markdown_content.strip():
        raise HTTPException(status_code=400, detail="Brief has no markdown content to render")

    structured = brief.get("structured_json") or {}
    pdf_bytes = render_brief_pdf(
        markdown_content=markdown_content,
        conversation_id=brief["conversation_id"],
        brief_id=brief["id"],
        brief_version=int(brief["version"]),
        jurisdiction=structured.get("jurisdiction") if isinstance(structured, dict) else None,
    )

    storage_path, signed_url = upload_brief_pdf_and_get_url(
        user_id=user_id,
        brief_id=brief["id"],
        pdf_bytes=pdf_bytes,
        expires_in=expires_in,
    )

    update_brief_pdf_path(user_id=user_id, brief_id=brief["id"], pdf_storage_path=storage_path)
    record_audit_event(
        user_id=user_id,
        conversation_id=brief["conversation_id"],
        event_type="brief.pdf_generated",
        event_payload={"brief_id": brief["id"], "storage_path": storage_path},
    )

    return BriefPDFResponse(
        brief_id=brief["id"],
        conversation_id=brief["conversation_id"],
        version=brief["version"],
        download_url=signed_url,
        expires_in=expires_in,
    )


# ============================================
# Legacy upload endpoint (kept for compatibility)
# ============================================


@app.post("/upload")
async def upload_file_legacy(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Legacy parse-only upload endpoint retained for backwards compatibility."""
    user_id = current_user["user_id"]
    _enforce_rate_limit("legacy_upload", user_id, limit=10, window_seconds=60)

    allowed_extensions = {".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg", ".gif", ".webp"}
    filename = file.filename or "unknown"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(allowed_extensions)}",
        )

    try:
        content = await file.read()
        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB",
            )

        parsed_content, content_type = parse_document(content, filename)

        return {
            "filename": filename,
            "content_type": content_type,
            "parsed_content": parsed_content,
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Legacy file upload failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to parse file")


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host=host, port=port)
