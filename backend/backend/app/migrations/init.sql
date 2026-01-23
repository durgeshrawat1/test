-- Create metadata tables if they don't exist
-- NOTE: Apply this file only in controlled environments. Set
-- the environment variable APPLY_INIT_SQL=true to run these
-- statements during startup or CI migration steps.
CREATE SCHEMA IF NOT EXISTS system;

CREATE TABLE IF NOT EXISTS system.schemas (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  access_group TEXT NOT NULL,
  physical_table_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS system.table_columns (
  id SERIAL PRIMARY KEY,
  schema_id INTEGER NOT NULL,
  column_name TEXT NOT NULL,
  data_type TEXT NOT NULL,
  required BOOLEAN DEFAULT FALSE,
  validation TEXT
);

CREATE TABLE IF NOT EXISTS system.schema_versions (
  id SERIAL PRIMARY KEY,
  schema_id INTEGER NOT NULL,
  version INTEGER NOT NULL,
  status TEXT NOT NULL, -- draft|final
  physical_table_name TEXT,
  created_by TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Add indexes for quick lookup
CREATE INDEX IF NOT EXISTS idx_system_schemas_physical_table ON system.schemas(physical_table_name);
CREATE INDEX IF NOT EXISTS idx_system_table_columns_schema ON system.table_columns(schema_id);
