-- Production foundation migration for conversations, briefs, documents, and auditability.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================
-- Conversations
-- ============================================
CREATE TABLE IF NOT EXISTS public.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT 'New Conversation',
    ui_mode TEXT NOT NULL DEFAULT 'chat' CHECK (ui_mode IN ('chat', 'analysis')),
    legal_topic TEXT NOT NULL DEFAULT 'general',
    user_state TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived', 'deleted')),
    last_message_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_created
    ON public.conversations(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_user_last_message
    ON public.conversations(user_id, last_message_at DESC NULLS LAST);

-- ============================================
-- Conversation Messages
-- ============================================
CREATE TABLE IF NOT EXISTS public.conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation_created
    ON public.conversation_messages(conversation_id, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_user_created
    ON public.conversation_messages(user_id, created_at DESC);

-- ============================================
-- Briefs
-- ============================================
CREATE TABLE IF NOT EXISTS public.briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'generated' CHECK (status IN ('generated', 'failed', 'deleted')),
    structured_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    markdown_content TEXT,
    html_content TEXT,
    pdf_storage_path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (conversation_id, version)
);

CREATE INDEX IF NOT EXISTS idx_briefs_user_created
    ON public.briefs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_briefs_conversation_version
    ON public.briefs(conversation_id, version DESC);

-- ============================================
-- Documents
-- ============================================
CREATE TABLE IF NOT EXISTS public.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES public.conversations(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    storage_path TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    mime_type TEXT,
    file_size_bytes BIGINT,
    sha256 TEXT,
    parsing_status TEXT NOT NULL DEFAULT 'pending' CHECK (
        parsing_status IN ('pending', 'parsed', 'failed', 'deleted')
    ),
    parsed_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_documents_user_created
    ON public.documents(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_conversation
    ON public.documents(conversation_id, created_at DESC);

-- ============================================
-- Audit Events
-- ============================================
CREATE TABLE IF NOT EXISTS public.audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES public.conversations(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    event_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_events_user_created
    ON public.audit_events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_type_created
    ON public.audit_events(event_type, created_at DESC);

-- ============================================
-- Retention Jobs (system-owned)
-- ============================================
CREATE TABLE IF NOT EXISTS public.retention_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    result JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_retention_jobs_created
    ON public.retention_jobs(created_at DESC);

-- ============================================
-- Update updated_at trigger for conversations
-- ============================================
CREATE OR REPLACE FUNCTION public.update_conversations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS conversations_updated_at ON public.conversations;
CREATE TRIGGER conversations_updated_at
    BEFORE UPDATE ON public.conversations
    FOR EACH ROW
    EXECUTE FUNCTION public.update_conversations_updated_at();

-- ============================================
-- RLS policies for user-owned data
-- ============================================
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversation_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.briefs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_events ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'conversations' AND policyname = 'conversations_owner_all'
    ) THEN
        CREATE POLICY conversations_owner_all
            ON public.conversations
            FOR ALL
            USING (auth.uid() = user_id)
            WITH CHECK (auth.uid() = user_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'conversation_messages' AND policyname = 'conversation_messages_owner_all'
    ) THEN
        CREATE POLICY conversation_messages_owner_all
            ON public.conversation_messages
            FOR ALL
            USING (auth.uid() = user_id)
            WITH CHECK (auth.uid() = user_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'briefs' AND policyname = 'briefs_owner_all'
    ) THEN
        CREATE POLICY briefs_owner_all
            ON public.briefs
            FOR ALL
            USING (auth.uid() = user_id)
            WITH CHECK (auth.uid() = user_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'documents' AND policyname = 'documents_owner_all'
    ) THEN
        CREATE POLICY documents_owner_all
            ON public.documents
            FOR ALL
            USING (auth.uid() = user_id)
            WITH CHECK (auth.uid() = user_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'audit_events' AND policyname = 'audit_events_owner_select'
    ) THEN
        CREATE POLICY audit_events_owner_select
            ON public.audit_events
            FOR SELECT
            USING (auth.uid() = user_id);
    END IF;
END $$;

-- ============================================
-- Private storage buckets and object policies
-- ============================================
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'documents',
    'documents',
    FALSE,
    10485760,
    ARRAY['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'image/png', 'image/jpeg', 'image/webp']::TEXT[]
)
ON CONFLICT (id) DO UPDATE SET
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'briefs',
    'briefs',
    FALSE,
    10485760,
    ARRAY['application/pdf']::TEXT[]
)
ON CONFLICT (id) DO UPDATE SET
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'storage' AND tablename = 'objects' AND policyname = 'documents_owner_access'
    ) THEN
        CREATE POLICY documents_owner_access
            ON storage.objects
            FOR ALL
            USING (bucket_id = 'documents' AND owner::text = auth.uid()::text)
            WITH CHECK (bucket_id = 'documents' AND owner::text = auth.uid()::text);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'storage' AND tablename = 'objects' AND policyname = 'briefs_owner_access'
    ) THEN
        CREATE POLICY briefs_owner_access
            ON storage.objects
            FOR ALL
            USING (bucket_id = 'briefs' AND owner::text = auth.uid()::text)
            WITH CHECK (bucket_id = 'briefs' AND owner::text = auth.uid()::text);
    END IF;
END $$;
