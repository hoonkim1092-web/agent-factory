-- Claude Code project memory sync table.
-- PC간 세션 연속성을 위한 메모리 동기화 테이블.
-- Apply once in Supabase SQL Editor.
--
-- Usage: scripts/sync_claude_memory.py --mode push/pull

CREATE TABLE IF NOT EXISTS claude_memory (
    project_id  TEXT        PRIMARY KEY,
    machine     TEXT        NOT NULL    DEFAULT 'unknown',
    updated_at  TIMESTAMPTZ NOT NULL    DEFAULT now(),
    files       JSONB       NOT NULL    DEFAULT '{}'::jsonb
    -- files format: {"MEMORY.md": {"content": "...", "mtime": "ISO"}, ...}
);

CREATE INDEX IF NOT EXISTS idx_claude_memory_updated_at
    ON claude_memory (updated_at DESC);

-- Row Level Security (service_role key로만 접근)
ALTER TABLE claude_memory ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role full access" ON claude_memory
    USING (true)
    WITH CHECK (true);
