-- Migration: create indexes to support fast schema and group searches
-- This file is applied only if APPLY_INIT_SQL=true in the environment and will
-- run during startup when requested. It is safe to run repeatedly (CREATE INDEX IF NOT EXISTS).

-- Index on schema name to accelerate `name ILIKE '%q%'` and prefix queries
CREATE INDEX IF NOT EXISTS idx_system_schemas_name ON system.schemas (lower(name));

-- Index on access_group to accelerate group-based filtering
CREATE INDEX IF NOT EXISTS idx_system_schemas_access_group ON system.schemas (access_group);

-- Optionally create a trigram index for faster substring searches (requires pg_trgm)
-- To enable, ensure the extension exists and uncomment the following lines in a controlled migration:
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- CREATE INDEX IF NOT EXISTS idx_system_schemas_name_trgm ON system.schemas USING gin (name gin_trgm_ops);
