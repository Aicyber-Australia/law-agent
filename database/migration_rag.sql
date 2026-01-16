-- AusLaw AI - RAG Database Migration
-- Run this in Supabase SQL Editor

-- Enable pgvector extension (already available in Supabase)
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- LEGISLATION DOCUMENTS TABLE
-- Stores metadata for legal documents
-- ============================================
CREATE TABLE legislation_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id TEXT UNIQUE NOT NULL,           -- From Hugging Face dataset
    citation TEXT NOT NULL,                     -- e.g., "Crimes Act 1900 (NSW)"
    jurisdiction TEXT NOT NULL,                 -- FEDERAL, NSW, QLD
    source TEXT,                                -- e.g., federal_register_of_legislation
    source_url TEXT,                            -- Original URL
    mime_type TEXT,                             -- text/html, application/pdf, etc.
    effective_date DATE,                        -- Document date from dataset
    full_text TEXT,                             -- Complete document text (for reference)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- LEGISLATION CHUNKS TABLE
-- Stores document chunks with embeddings and parent-child hierarchy
-- ============================================
CREATE TABLE legislation_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES legislation_documents(id) ON DELETE CASCADE,
    parent_chunk_id UUID REFERENCES legislation_chunks(id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    embedding vector(1536),                     -- OpenAI text-embedding-3-small
    chunk_type TEXT NOT NULL DEFAULT 'child',   -- 'parent' or 'child'
    chunk_index INTEGER NOT NULL,               -- Order within document
    token_count INTEGER,                        -- Actual token count
    metadata JSONB DEFAULT '{}',                -- Additional metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- FULL-TEXT SEARCH COLUMN (Generated)
-- ============================================
ALTER TABLE legislation_chunks
ADD COLUMN content_tsv tsvector
GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

-- ============================================
-- INDEXES
-- ============================================

-- Vector similarity search index (HNSW for approximate nearest neighbor)
CREATE INDEX idx_chunks_embedding ON legislation_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Full-text search index
CREATE INDEX idx_chunks_tsv ON legislation_chunks USING GIN (content_tsv);

-- Foreign key and filter indexes
CREATE INDEX idx_chunks_document_id ON legislation_chunks(document_id);
CREATE INDEX idx_chunks_parent_id ON legislation_chunks(parent_chunk_id);
CREATE INDEX idx_chunks_type ON legislation_chunks(chunk_type);
CREATE INDEX idx_docs_jurisdiction ON legislation_documents(jurisdiction);
CREATE INDEX idx_docs_version_id ON legislation_documents(version_id);

-- ============================================
-- HYBRID SEARCH FUNCTION
-- Combines vector similarity and keyword search with RRF fusion
-- Now searches both child chunks AND parent-only chunks (small docs)
-- ============================================
CREATE OR REPLACE FUNCTION hybrid_search(
    query_embedding vector(1536),
    query_text TEXT,
    filter_jurisdiction TEXT DEFAULT NULL,
    match_count INTEGER DEFAULT 20
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    parent_chunk_id UUID,
    content TEXT,
    chunk_type TEXT,
    citation TEXT,
    jurisdiction TEXT,
    source_url TEXT,
    vector_rank INTEGER,
    keyword_rank INTEGER,
    vector_similarity FLOAT,
    keyword_score FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH vector_results AS (
        SELECT
            c.id,
            c.document_id,
            c.parent_chunk_id,
            c.content,
            c.chunk_type,
            d.citation,
            d.jurisdiction,
            d.source_url,
            ROW_NUMBER() OVER (ORDER BY c.embedding <=> query_embedding)::INTEGER as rank,
            (1 - (c.embedding <=> query_embedding))::FLOAT as similarity
        FROM legislation_chunks c
        JOIN legislation_documents d ON c.document_id = d.id
        WHERE c.embedding IS NOT NULL
          -- Search child chunks OR parent chunks that have no children (small docs)
          AND (c.chunk_type = 'child' OR (c.chunk_type = 'parent' AND NOT EXISTS (
              SELECT 1 FROM legislation_chunks child WHERE child.parent_chunk_id = c.id
          )))
          AND (filter_jurisdiction IS NULL OR d.jurisdiction = filter_jurisdiction)
        ORDER BY c.embedding <=> query_embedding
        LIMIT match_count
    ),
    keyword_results AS (
        SELECT
            c.id,
            c.document_id,
            c.parent_chunk_id,
            c.content,
            c.chunk_type,
            d.citation,
            d.jurisdiction,
            d.source_url,
            ROW_NUMBER() OVER (ORDER BY ts_rank(c.content_tsv, websearch_to_tsquery('english', query_text)) DESC)::INTEGER as rank,
            ts_rank(c.content_tsv, websearch_to_tsquery('english', query_text))::FLOAT as score
        FROM legislation_chunks c
        JOIN legislation_documents d ON c.document_id = d.id
        WHERE c.content_tsv @@ websearch_to_tsquery('english', query_text)
          -- Search child chunks OR parent chunks that have no children (small docs)
          AND (c.chunk_type = 'child' OR (c.chunk_type = 'parent' AND NOT EXISTS (
              SELECT 1 FROM legislation_chunks child WHERE child.parent_chunk_id = c.id
          )))
          AND (filter_jurisdiction IS NULL OR d.jurisdiction = filter_jurisdiction)
        ORDER BY ts_rank(c.content_tsv, websearch_to_tsquery('english', query_text)) DESC
        LIMIT match_count
    )
    SELECT
        COALESCE(v.id, k.id) as chunk_id,
        COALESCE(v.document_id, k.document_id) as document_id,
        COALESCE(v.parent_chunk_id, k.parent_chunk_id) as parent_chunk_id,
        COALESCE(v.content, k.content) as content,
        COALESCE(v.chunk_type, k.chunk_type) as chunk_type,
        COALESCE(v.citation, k.citation) as citation,
        COALESCE(v.jurisdiction, k.jurisdiction) as jurisdiction,
        COALESCE(v.source_url, k.source_url) as source_url,
        v.rank as vector_rank,
        k.rank as keyword_rank,
        v.similarity as vector_similarity,
        k.score as keyword_score
    FROM vector_results v
    FULL OUTER JOIN keyword_results k ON v.id = k.id;
END;
$$;

-- ============================================
-- HELPER FUNCTION: Get parent chunk content
-- ============================================
CREATE OR REPLACE FUNCTION get_parent_content(child_chunk_id UUID)
RETURNS TEXT
LANGUAGE plpgsql
AS $$
DECLARE
    parent_content TEXT;
    parent_id UUID;
BEGIN
    -- Get parent chunk ID
    SELECT parent_chunk_id INTO parent_id
    FROM legislation_chunks
    WHERE id = child_chunk_id;

    IF parent_id IS NULL THEN
        -- No parent, return the child content
        SELECT content INTO parent_content
        FROM legislation_chunks
        WHERE id = child_chunk_id;
    ELSE
        -- Return parent content
        SELECT content INTO parent_content
        FROM legislation_chunks
        WHERE id = parent_id;
    END IF;

    RETURN parent_content;
END;
$$;

-- ============================================
-- UPDATE TIMESTAMP TRIGGER
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER legislation_documents_updated_at
    BEFORE UPDATE ON legislation_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================
-- ROW LEVEL SECURITY (Optional - enable if needed)
-- ============================================
-- ALTER TABLE legislation_documents ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE legislation_chunks ENABLE ROW LEVEL SECURITY;

-- CREATE POLICY "Allow public read access to legislation_documents"
--     ON legislation_documents FOR SELECT
--     USING (true);

-- CREATE POLICY "Allow public read access to legislation_chunks"
--     ON legislation_chunks FOR SELECT
--     USING (true);
