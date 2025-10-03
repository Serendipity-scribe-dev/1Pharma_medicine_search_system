-- schema.sql
-- Run this on the target Postgres (>= 12 recommended)

-- 1. Create extensions (requires superuser)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

DROP TABLE IF EXISTS search_medicines;
CREATE TABLE medicines (
  id              TEXT PRIMARY KEY,
  sku_id          TEXT,
  name            TEXT NOT NULL,
  manufacturer_name TEXT,
  marketer_name   TEXT,
  type            TEXT,
  price           NUMERIC,
  pack_size_label TEXT,
  short_composition TEXT,
  is_discontinued BOOLEAN,
  available       BOOLEAN,
  name_tsv        tsvector -- materialised tsvector for full-text
);


-- 2) create tsvector trigger function (updates name_tsv)
CREATE OR REPLACE FUNCTION search_medicine_tsv_trigger()
RETURNS trigger
AS $$
BEGIN
    -- name is weight A, short_composition is weight B
    NEW.name_tsv :=
        setweight(to_tsvector('simple', coalesce(NEW.name, '')), 'A')
        || setweight(to_tsvector('simple', coalesce(NEW.short_composition, '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3) trigger to update name_tsv on insert/update
DROP TRIGGER IF EXISTS tsvectorupdate ON search_medicine;
CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE
  ON search_medicine FOR EACH ROW EXECUTE FUNCTION search_medicine_tsv_trigger();

  -- 4) Indexes

-- 4.a B-tree functional index for prefix search (case-insensitive)
-- We use lower(name) with text_pattern_ops to optimize left-anchored LIKE queries.
CREATE INDEX IF NOT EXISTS idx_search_medicine_lower_name_btree
  ON search_medicine (lower(name) text_pattern_ops);

  -- 4.b GIN trigram index to accelerate substring (ILIKE '%...%') and similarity()
CREATE INDEX IF NOT EXISTS idx_search_medicine_name_trgm
  ON search_medicine USING gin (name gin_trgm_ops);

  -- 4.c GIN index on name_tsv for full-text search
CREATE INDEX IF NOT EXISTS idx_search_medicine_name_tsv
  ON search_medicine USING gin (name_tsv);

-- First, make sure unaccent is enabled
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Create an IMMUTABLE wrapper around unaccent
CREATE OR REPLACE FUNCTION immutable_unaccent(text)
RETURNS text AS $$
BEGIN
    RETURN unaccent($1);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Optional: index on lower(unaccent(name)) for highly normalized fuzzy match
CREATE INDEX IF NOT EXISTS idx_search_medicine_name_unaccent
ON search_medicine
USING gin (immutable_unaccent(lower(name)) gin_trgm_ops);

EXPLAIN ANALYZE SELECT id, name FROM search_medicine WHERE lower(name) LIKE 'boc%' LIMIT 10;
