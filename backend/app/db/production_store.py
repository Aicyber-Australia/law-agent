"""Persistence helpers for production conversation and brief data."""

from __future__ import annotations

import hashlib
import copy
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from urllib.parse import quote

import httpx
from langchain_openai import ChatOpenAI

from app.config import (
    SUPABASE_KEY,
    SUPABASE_URL,
    DOCUMENTS_BUCKET,
    BRIEF_PDF_BUCKET,
    logger,
)
from app.db import supabase


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_uuid(value: Optional[str]) -> str:
    if value:
        return str(uuid.UUID(value))
    return str(uuid.uuid4())


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY,
    }


def _topic_default_title(legal_topic: Optional[str] = None) -> str:
    topic_defaults = {
        "parking_ticket": "Parking Ticket Help",
        "insurance_claim": "Insurance Claim Help",
        "general": "General Legal Help",
    }
    return topic_defaults.get((legal_topic or "general").lower(), "Legal Help")


def _normalize_text_for_compare(value: Optional[str]) -> str:
    normalized = (value or "").lower()
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _is_low_signal_message(content: Optional[str]) -> bool:
    """
    Detect greetings/pleasantries that are poor conversation-title candidates.
    """
    normalized = _normalize_text_for_compare(content)
    if not normalized:
        return True

    low_signal_phrases = {
        "hi",
        "hello",
        "hey",
        "hi there",
        "hello there",
        "hey there",
        "good morning",
        "good afternoon",
        "good evening",
        "thanks",
        "thank you",
    }
    if normalized in low_signal_phrases:
        return True

    low_signal_tokens = {
        "hi",
        "hello",
        "hey",
        "yo",
        "hiya",
        "sup",
        "good",
        "morning",
        "afternoon",
        "evening",
        "thanks",
        "thank",
        "you",
        "please",
        "ok",
        "okay",
        "there",
    }
    tokens = normalized.split()
    return len(tokens) <= 3 and all(token in low_signal_tokens for token in tokens)


def _clean_message_for_title(content: Optional[str]) -> str:
    cleaned = (content or "").strip()
    cleaned = re.sub(r"\[[A-Z_]+\]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def is_generic_conversation_title(*, title: Optional[str], legal_topic: Optional[str] = None) -> bool:
    """
    Return True when a title is a placeholder/generic value and can be upgraded.
    """
    normalized = _normalize_text_for_compare(title)
    if not normalized:
        return True

    generic_titles = {
        "new conversation",
        "untitled conversation",
        "conversation",
        "legal help",
        "general legal help",
        "parking ticket help",
        "insurance claim help",
        _normalize_text_for_compare(_topic_default_title(legal_topic)),
    }

    if normalized in generic_titles:
        return True
    return _is_low_signal_message(title)


def _finalize_title_candidate(
    *,
    raw_title: Optional[str],
    legal_topic: Optional[str] = None,
    max_words: int = 12,
    max_chars: int = 72,
) -> str:
    candidate = _clean_message_for_title(raw_title)
    if candidate.startswith(("'", '"', "`")) and candidate.endswith(("'", '"', "`")) and len(candidate) > 1:
        candidate = candidate[1:-1].strip()
    candidate = re.sub(r"\s+", " ", candidate).strip(" -:;,.")

    if not candidate or _is_low_signal_message(candidate):
        return _topic_default_title(legal_topic)

    words = candidate.split()
    title = " ".join(words[:max_words])
    if len(words) > max_words:
        title += "..."
    if len(title) > max_chars:
        title = title[: max_chars - 3].rstrip() + "..."
    if title:
        title = title[0].upper() + title[1:]
    return title or _topic_default_title(legal_topic)


def _extract_text_content(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return " ".join(parts).strip()
    return str(content or "").strip()


def _build_non_emitting_llm_config(run_config: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """
    Build a config that suppresses internal LLM event emission to chat.
    """
    cfg: dict[str, Any] = copy.copy(run_config) if run_config else {}
    metadata = dict(cfg.get("metadata") or {})
    metadata["emit-messages"] = False
    metadata["emit-tool-calls"] = False
    # Keep prefixed keys for compatibility with copilotkit config conventions.
    metadata["copilotkit:emit-messages"] = False
    metadata["copilotkit:emit-tool-calls"] = False
    cfg["metadata"] = metadata
    return cfg


def suggest_conversation_title_with_llm(
    *,
    user_messages: list[str],
    legal_topic: Optional[str] = None,
    run_config: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    """
    Generate a concise conversation title from early user turns.
    Returns None if generation fails.
    """
    cleaned_messages = [_clean_message_for_title(m) for m in user_messages if _clean_message_for_title(m)]
    if not cleaned_messages:
        return None

    meaningful_messages = [m for m in cleaned_messages if not _is_low_signal_message(m)]
    if not meaningful_messages:
        return _topic_default_title(legal_topic)

    transcript = "\n".join(f"{idx + 1}. {msg}" for idx, msg in enumerate(meaningful_messages[:6]))
    prompt = (
        "You write concise topic labels for a legal assistant conversation.\n"
        "Rules:\n"
        "- 4 to 12 words.\n"
        "- Never exceed 19 words.\n"
        "- Return a topic label, not a full sentence.\n"
        "- Avoid first-person phrasing like 'I need help with...'.\n"
        "- Be specific to the legal issue or dispute.\n"
        "- No surrounding quotes.\n"
        "- No trailing punctuation.\n"
        "- Return title only.\n\n"
        f"Legal topic hint: {legal_topic or 'general'}\n"
        "User messages:\n"
        f"{transcript}\n"
    )

    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=24)
        response = llm.invoke(prompt, config=_build_non_emitting_llm_config(run_config))
        text = _extract_text_content(response)
        return _finalize_title_candidate(raw_title=text, legal_topic=legal_topic)
    except Exception as exc:
        logger.debug("LLM title generation failed: %s", exc)
        return None


def suggest_conversation_title(
    *,
    content: str,
    legal_topic: Optional[str] = None,
    max_words: int = 12,
    max_chars: int = 72,
) -> str:
    """Generate a short, readable conversation title from user input."""
    return _finalize_title_candidate(
        raw_title=content,
        legal_topic=legal_topic,
        max_words=max_words,
        max_chars=max_chars,
    )


def create_conversation(
    *,
    user_id: str,
    conversation_id: Optional[str] = None,
    title: str = "New Conversation",
    ui_mode: str = "chat",
    legal_topic: str = "general",
    user_state: Optional[str] = None,
) -> dict[str, Any]:
    conv_id = _as_uuid(conversation_id)
    existing = (
        supabase.table("conversations")
        .select("id,title,ui_mode,legal_topic,user_state,status,last_message_at,created_at,updated_at")
        .eq("id", conv_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]

    payload = {
        "id": conv_id,
        "user_id": user_id,
        "title": title,
        "ui_mode": ui_mode,
        "legal_topic": legal_topic,
        "user_state": user_state,
        "status": "active",
        "last_message_at": _utc_now_iso(),
    }

    try:
        result = supabase.table("conversations").insert(payload).execute()
        if not result.data:
            raise RuntimeError("Failed to create conversation")
        return result.data[0]
    except Exception:
        # Handle insert races gracefully by returning existing row if present.
        race = (
            supabase.table("conversations")
            .select("id,title,ui_mode,legal_topic,user_state,status,last_message_at,created_at,updated_at")
            .eq("id", conv_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if race.data:
            return race.data[0]
        raise


def get_conversation_owner(conversation_id: str) -> Optional[str]:
    """Resolve conversation owner id when user context is missing in agent state."""
    try:
        result = (
            supabase.table("conversations")
            .select("user_id")
            .eq("id", conversation_id)
            .limit(1)
            .execute()
        )
    except Exception:
        return None

    if not result.data:
        return None
    return result.data[0].get("user_id")


def touch_conversation(
    *,
    user_id: str,
    conversation_id: str,
    title: Optional[str] = None,
    status: Optional[str] = None,
    ui_mode: Optional[str] = None,
    legal_topic: Optional[str] = None,
    user_state: Optional[str] = None,
) -> None:
    updates: dict[str, Any] = {
        "last_message_at": _utc_now_iso(),
        "updated_at": _utc_now_iso(),
    }
    if title is not None:
        updates["title"] = title
    if status is not None:
        updates["status"] = status
    if ui_mode is not None:
        updates["ui_mode"] = ui_mode
    if legal_topic is not None:
        updates["legal_topic"] = legal_topic
    if user_state is not None:
        updates["user_state"] = user_state

    (
        supabase.table("conversations")
        .update(updates)
        .eq("id", conversation_id)
        .eq("user_id", user_id)
        .execute()
    )


def list_conversations(*, user_id: str, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    result = (
        supabase.table("conversations")
        .select("id,title,ui_mode,legal_topic,user_state,status,last_message_at,created_at,updated_at")
        .eq("user_id", user_id)
        .neq("status", "deleted")
        .order("last_message_at", desc=True)
        .range(offset, offset + max(limit - 1, 0))
        .execute()
    )
    return result.data or []


def get_conversation(
    *,
    user_id: str,
    conversation_id: str,
    message_limit: int = 100,
) -> dict[str, Any] | None:
    conversation_result = (
        supabase.table("conversations")
        .select("id,title,ui_mode,legal_topic,user_state,status,last_message_at,created_at,updated_at")
        .eq("id", conversation_id)
        .eq("user_id", user_id)
        .neq("status", "deleted")
        .limit(1)
        .execute()
    )

    if not conversation_result.data:
        return None

    message_result = (
        supabase.table("conversation_messages")
        .select("id,role,content,metadata,created_at")
        .eq("conversation_id", conversation_id)
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .limit(message_limit)
        .execute()
    )

    brief_result = (
        supabase.table("briefs")
        .select("id,version,status,created_at,generated_at,pdf_storage_path")
        .eq("conversation_id", conversation_id)
        .eq("user_id", user_id)
        .neq("status", "deleted")
        .order("version", desc=True)
        .limit(1)
        .execute()
    )

    conversation = conversation_result.data[0]
    conversation["messages"] = message_result.data or []
    conversation["latest_brief"] = (brief_result.data or [None])[0]
    return conversation


def update_conversation(
    *,
    user_id: str,
    conversation_id: str,
    title: Optional[str] = None,
    status: Optional[str] = None,
    ui_mode: Optional[str] = None,
    legal_topic: Optional[str] = None,
    user_state: Optional[str] = None,
) -> dict[str, Any] | None:
    updates: dict[str, Any] = {"updated_at": _utc_now_iso()}
    if title is not None:
        updates["title"] = title
    if status is not None:
        updates["status"] = status
    if ui_mode is not None:
        updates["ui_mode"] = ui_mode
    if legal_topic is not None:
        updates["legal_topic"] = legal_topic
    if user_state is not None:
        updates["user_state"] = user_state

    result = (
        supabase.table("conversations")
        .update(updates)
        .eq("id", conversation_id)
        .eq("user_id", user_id)
        .execute()
    )
    return (result.data or [None])[0]


def soft_delete_conversation(*, user_id: str, conversation_id: str) -> bool:
    result = (
        supabase.table("conversations")
        .update(
            {
                "status": "deleted",
                "deleted_at": _utc_now_iso(),
                "updated_at": _utc_now_iso(),
            }
        )
        .eq("id", conversation_id)
        .eq("user_id", user_id)
        .execute()
    )
    return bool(result.data)


def add_message(
    *,
    user_id: str,
    conversation_id: str,
    role: str,
    content: str,
    metadata: Optional[dict[str, Any]] = None,
    run_config: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    payload = {
        "conversation_id": conversation_id,
        "user_id": user_id,
        "role": role,
        "content": content,
        "metadata": metadata or {},
    }
    result = supabase.table("conversation_messages").insert(payload).execute()
    if not result.data:
        raise RuntimeError("Failed to save message")

    title_update: Optional[str] = None
    if role == "user":
        try:
            conversation_result = (
                supabase.table("conversations")
                .select("title,legal_topic")
                .eq("id", conversation_id)
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            if conversation_result.data:
                current_title = (conversation_result.data[0].get("title") or "").strip()
                legal_topic = conversation_result.data[0].get("legal_topic")
                if is_generic_conversation_title(title=current_title, legal_topic=legal_topic):
                    user_messages_result = (
                        supabase.table("conversation_messages")
                        .select("content")
                        .eq("conversation_id", conversation_id)
                        .eq("user_id", user_id)
                        .eq("role", "user")
                        .order("created_at", desc=False)
                        .limit(4)
                        .execute()
                    )
                    user_messages = [
                        (item.get("content") or "")
                        for item in (user_messages_result.data or [])
                        if (item.get("content") or "").strip()
                    ]

                    suggested_title = None
                    if len(user_messages) >= 1:
                        suggested_title = suggest_conversation_title_with_llm(
                            user_messages=user_messages,
                            legal_topic=legal_topic,
                            run_config=run_config,
                        )

                    if not suggested_title:
                        meaningful_messages = [m for m in user_messages if not _is_low_signal_message(m)]
                        fallback_source = meaningful_messages[-1] if meaningful_messages else content
                        suggested_title = suggest_conversation_title(
                            content=fallback_source,
                            legal_topic=legal_topic,
                        )
                    if _normalize_text_for_compare(suggested_title) != _normalize_text_for_compare(current_title):
                        title_update = suggested_title
        except Exception as exc:
            logger.debug("Unable to auto-title conversation %s: %s", conversation_id, exc)

    touch_conversation(
        user_id=user_id,
        conversation_id=conversation_id,
        status="active",
        title=title_update,
    )
    return result.data[0]


def record_audit_event(
    *,
    user_id: str,
    event_type: str,
    event_payload: Optional[dict[str, Any]] = None,
    conversation_id: Optional[str] = None,
) -> None:
    payload = {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "event_type": event_type,
        "event_payload": event_payload or {},
    }
    supabase.table("audit_events").insert(payload).execute()


def save_brief(
    *,
    user_id: str,
    conversation_id: str,
    structured_json: dict[str, Any],
    markdown_content: str,
    html_content: Optional[str] = None,
    status: str = "generated",
) -> dict[str, Any]:
    latest_result = (
        supabase.table("briefs")
        .select("version")
        .eq("conversation_id", conversation_id)
        .eq("user_id", user_id)
        .order("version", desc=True)
        .limit(1)
        .execute()
    )
    latest_version = (latest_result.data or [{"version": 0}])[0]["version"]
    version = int(latest_version) + 1

    payload = {
        "conversation_id": conversation_id,
        "user_id": user_id,
        "version": version,
        "status": status,
        "structured_json": structured_json,
        "markdown_content": markdown_content,
        "html_content": html_content,
        "generated_at": _utc_now_iso(),
    }
    result = supabase.table("briefs").insert(payload).execute()
    if not result.data:
        raise RuntimeError("Failed to save brief")

    record_audit_event(
        user_id=user_id,
        conversation_id=conversation_id,
        event_type="brief.generated",
        event_payload={"brief_id": result.data[0]["id"], "version": version},
    )
    return result.data[0]


def get_brief(*, user_id: str, brief_id: str) -> dict[str, Any] | None:
    result = (
        supabase.table("briefs")
        .select("*")
        .eq("id", brief_id)
        .eq("user_id", user_id)
        .neq("status", "deleted")
        .limit(1)
        .execute()
    )
    return (result.data or [None])[0]


def update_brief_pdf_path(*, user_id: str, brief_id: str, pdf_storage_path: str) -> dict[str, Any] | None:
    result = (
        supabase.table("briefs")
        .update({"pdf_storage_path": pdf_storage_path})
        .eq("id", brief_id)
        .eq("user_id", user_id)
        .execute()
    )
    return (result.data or [None])[0]


def get_latest_brief_for_conversation(*, user_id: str, conversation_id: str) -> dict[str, Any] | None:
    result = (
        supabase.table("briefs")
        .select("id,version,status,created_at,generated_at,pdf_storage_path")
        .eq("conversation_id", conversation_id)
        .eq("user_id", user_id)
        .neq("status", "deleted")
        .order("version", desc=True)
        .limit(1)
        .execute()
    )
    return (result.data or [None])[0]


def create_document_record(
    *,
    user_id: str,
    storage_path: str,
    original_filename: str,
    mime_type: Optional[str],
    file_size_bytes: int,
    conversation_id: Optional[str] = None,
    parsed_text: Optional[str] = None,
    parsing_status: str = "pending",
    sha256: Optional[str] = None,
) -> dict[str, Any]:
    payload = {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "storage_path": storage_path,
        "original_filename": original_filename,
        "mime_type": mime_type,
        "file_size_bytes": file_size_bytes,
        "sha256": sha256,
        "parsed_text": parsed_text,
        "parsing_status": parsing_status,
    }
    result = supabase.table("documents").insert(payload).execute()
    if not result.data:
        raise RuntimeError("Failed to create document record")

    record_audit_event(
        user_id=user_id,
        conversation_id=conversation_id,
        event_type="document.uploaded",
        event_payload={"document_id": result.data[0]["id"], "storage_path": storage_path},
    )
    return result.data[0]


def get_document(*, user_id: str, document_id: str) -> dict[str, Any] | None:
    result = (
        supabase.table("documents")
        .select("*")
        .eq("id", document_id)
        .eq("user_id", user_id)
        .is_("deleted_at", None)
        .limit(1)
        .execute()
    )
    return (result.data or [None])[0]


def compute_sha256(content: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(content)
    return digest.hexdigest()


def upload_private_object(
    *,
    bucket: str,
    storage_path: str,
    content: bytes,
    content_type: str,
    upsert: bool = False,
) -> None:
    quoted_path = quote(storage_path, safe="/")
    endpoint = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{quoted_path}"
    headers = {
        **_auth_headers(),
        "Content-Type": content_type,
        "x-upsert": "true" if upsert else "false",
    }

    response = httpx.post(endpoint, content=content, headers=headers, timeout=60)
    if response.status_code >= 400:
        logger.error(
            "Storage upload failed: bucket=%s path=%s status=%s body=%s",
            bucket,
            storage_path,
            response.status_code,
            response.text,
        )
    response.raise_for_status()


def create_signed_download_url(
    *,
    bucket: str,
    storage_path: str,
    expires_in: int = 900,
) -> str:
    quoted_path = quote(storage_path, safe="/")
    endpoint = f"{SUPABASE_URL}/storage/v1/object/sign/{bucket}/{quoted_path}"
    response = httpx.post(
        endpoint,
        json={"expiresIn": expires_in},
        headers=_auth_headers(),
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    signed = data.get("signedURL") or data.get("signedUrl")
    if not signed:
        raise RuntimeError("Storage API did not return signed URL")

    if signed.startswith("http://") or signed.startswith("https://"):
        return signed

    if signed.startswith("/"):
        return f"{SUPABASE_URL}/storage/v1{signed}"

    return f"{SUPABASE_URL}/storage/v1/{signed}"


def upload_document_and_create_record(
    *,
    user_id: str,
    original_filename: str,
    mime_type: str,
    content: bytes,
    conversation_id: Optional[str] = None,
    parsed_text: Optional[str] = None,
    parsing_status: str = "pending",
) -> dict[str, Any]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    doc_id = str(uuid.uuid4())
    safe_name = "".join(ch if ch.isalnum() or ch in ".-_" else "_" for ch in original_filename)
    storage_path = f"{user_id}/{timestamp}_{doc_id}_{safe_name}"

    upload_private_object(
        bucket=DOCUMENTS_BUCKET,
        storage_path=storage_path,
        content=content,
        content_type=mime_type,
        upsert=False,
    )

    return create_document_record(
        user_id=user_id,
        conversation_id=conversation_id,
        storage_path=storage_path,
        original_filename=original_filename,
        mime_type=mime_type,
        file_size_bytes=len(content),
        parsed_text=parsed_text,
        parsing_status=parsing_status,
        sha256=compute_sha256(content),
    )


def upload_brief_pdf_and_get_url(
    *,
    user_id: str,
    brief_id: str,
    pdf_bytes: bytes,
    expires_in: int = 900,
) -> tuple[str, str]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    storage_path = f"{user_id}/{timestamp}_{brief_id}.pdf"

    upload_private_object(
        bucket=BRIEF_PDF_BUCKET,
        storage_path=storage_path,
        content=pdf_bytes,
        content_type="application/pdf",
        upsert=True,
    )

    signed_url = create_signed_download_url(
        bucket=BRIEF_PDF_BUCKET,
        storage_path=storage_path,
        expires_in=expires_in,
    )
    return storage_path, signed_url


def run_retention_cleanup(*, retention_days: int) -> dict[str, Any]:
    """Apply soft-delete and hard-delete retention windows."""
    now = datetime.now(timezone.utc)
    soft_cutoff = (now - timedelta(days=retention_days)).isoformat()
    hard_cutoff = (now - timedelta(days=retention_days + 7)).isoformat()
    started_at = now.isoformat()

    job = (
        supabase.table("retention_jobs")
        .insert(
            {
                "job_type": "retention_cleanup",
                "status": "running",
                "started_at": started_at,
            }
        )
        .execute()
    )
    job_id = (job.data or [{}])[0].get("id")

    counts: dict[str, int] = {
        "conversations_soft_deleted": 0,
        "briefs_soft_deleted": 0,
        "documents_soft_deleted": 0,
        "messages_hard_deleted": 0,
        "briefs_hard_deleted": 0,
        "documents_hard_deleted": 0,
        "conversations_hard_deleted": 0,
    }

    try:
        soft_conversations = (
            supabase.table("conversations")
            .update(
                {
                    "status": "deleted",
                    "deleted_at": _utc_now_iso(),
                    "updated_at": _utc_now_iso(),
                }
            )
            .neq("status", "deleted")
            .lt("last_message_at", soft_cutoff)
            .execute()
        )
        soft_conversations_no_activity = (
            supabase.table("conversations")
            .update(
                {
                    "status": "deleted",
                    "deleted_at": _utc_now_iso(),
                    "updated_at": _utc_now_iso(),
                }
            )
            .neq("status", "deleted")
            .is_("last_message_at", None)
            .lt("created_at", soft_cutoff)
            .execute()
        )
        counts["conversations_soft_deleted"] = len(soft_conversations.data or []) + len(
            soft_conversations_no_activity.data or []
        )

        soft_briefs = (
            supabase.table("briefs")
            .update({"status": "deleted"})
            .neq("status", "deleted")
            .lt("created_at", soft_cutoff)
            .execute()
        )
        counts["briefs_soft_deleted"] = len(soft_briefs.data or [])

        soft_documents = (
            supabase.table("documents")
            .update(
                {
                    "deleted_at": _utc_now_iso(),
                    "parsing_status": "deleted",
                }
            )
            .is_("deleted_at", None)
            .lt("created_at", soft_cutoff)
            .execute()
        )
        counts["documents_soft_deleted"] = len(soft_documents.data or [])

        hard_messages = (
            supabase.table("conversation_messages")
            .delete()
            .lt("created_at", hard_cutoff)
            .execute()
        )
        counts["messages_hard_deleted"] = len(hard_messages.data or [])

        hard_briefs = (
            supabase.table("briefs")
            .delete()
            .eq("status", "deleted")
            .lt("created_at", hard_cutoff)
            .execute()
        )
        counts["briefs_hard_deleted"] = len(hard_briefs.data or [])

        hard_documents = (
            supabase.table("documents")
            .delete()
            .lt("deleted_at", hard_cutoff)
            .execute()
        )
        counts["documents_hard_deleted"] = len(hard_documents.data or [])

        hard_conversations = (
            supabase.table("conversations")
            .delete()
            .eq("status", "deleted")
            .lt("deleted_at", hard_cutoff)
            .execute()
        )
        counts["conversations_hard_deleted"] = len(hard_conversations.data or [])

        if job_id:
            supabase.table("retention_jobs").update(
                {
                    "status": "completed",
                    "finished_at": _utc_now_iso(),
                    "result": counts,
                }
            ).eq("id", job_id).execute()
        return {"job_id": job_id, "status": "completed", "result": counts}
    except Exception as exc:
        logger.error("Retention cleanup failed: %s", exc)
        if job_id:
            supabase.table("retention_jobs").update(
                {
                    "status": "failed",
                    "finished_at": _utc_now_iso(),
                    "result": {**counts, "error": str(exc)},
                }
            ).eq("id", job_id).execute()
        raise
