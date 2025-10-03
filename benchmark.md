# Benchmark Report

This benchmark evaluates the performance of our Django + PostgreSQL–based medicine search system. The search supports four query types:

- Prefix search → istartswith + B-Tree index

- Substring search → icontains + trigram (pg_trgm) index

- Fuzzy search → TrigramSimilarity + trigram index

- Full-text search → PostgreSQL to_tsvector with GIN index

### Why PostgreSQL ?

- Native full-text search (GIN + tsvector).

- Trigram similarity (pg_trgm) for substring and fuzzy search.

- Optimized B-Tree indexes for prefix lookups.

---

## Setup

- Framework: Django 5.x

- Database: PostgreSQL 15

- Database Design :
  Data imported from JSON into a single normalized table:

  ```bash
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
  name_tsv        tsvector
    );

  ```

- Extensions enabled:

```bash
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
```

- Indexes created:

```bash
# Prefix search optimization
CREATE INDEX idx_medicine_name_lower
  ON search_medicine (LOWER(name) varchar_pattern_ops);

# Substring & Fuzzy search optimization
CREATE INDEX idx_medicine_name_trgm
  ON search_medicine USING GIN (name gin_trgm_ops);

# Full-text search optimization
CREATE INDEX idx_medicine_name_tsv
  ON search_medicine USING GIN (name_tsv);

```

---

## Query Implementation

Each search type was mapped to the most efficient PostgreSQL operator:

- Prefix search → WHERE LOWER(name) LIKE 'par%' (B-Tree optimized)

- Substring search → WHERE name ILIKE '%para%' (accelerated by trigram index)

- Fuzzy search → WHERE SIMILARITY(name, 'paracetamol') > 0.3 ORDER BY SIMILARITY(...) DESC

- Full-text search → WHERE name_tsv @@ plainto_tsquery('english', 'injection')

---

## Benchmark Results

- A benchmarking script executed queries from benchmark_queries.json.

- Each query was run multiple times to calculate an average.

- Results were saved in:

      - submission.json → final answers for each query.

      - benchmark_timings.json → raw timing results (latency per query in ms).

  Example benchmark_timings.json output:

```bash
{
  "1": 167.04,
  "2": 241.84,
  "3": 222.28,
  "4": 432.97,
  "5": 14.69
}
```

| Query ID | Query Type  | Avg Latency (ms) | Notes                                                                                     |
| -------- | ----------- | ---------------- | ----------------------------------------------------------------------------------------- |
| **1**    | Prefix      | 167.04           | Performs well but slower than expected for indexed lookups (likely due to dataset size).  |
| **2**    | Substring   | 241.84           | Substring with trigram search is heavier; ~240ms avg.                                     |
| **3**    | Fuzzy       | 222.28           | Fuzzy similarity scoring increases cost.                                                  |
| **4**    | Full-text   | 432.97           | Full-text search is the slowest; GIN helps but tsvector building + ranking adds overhead. |
| **5**    | Small query | 14.69            | Very fast when exact match / small candidate set.                                         |

---

## Observations

- Exact/small queries (Case 5) run very fast (~15ms).

- Prefix search (Case 1), though indexed, shows ~167ms — suggesting PostgreSQL is scanning more candidates than expected.

- Substring (Case 2) and Fuzzy (Case 3) queries are costly since trigrams expand comparisons across many rows.

- Full-text (Case 4) is the slowest (~433ms avg). While GIN helps, ranking results (ts_rank) adds noticeable latency.

- For larger datasets, tuning Postgres parameters (work_mem, maintenance_work_mem) and using materialized search vectors could reduce latency.

---

## Run Instructions

```bash
# Run migrations and import dataset
python manage.py migrate
python import_data.py

# Run benchmark
python manage.py run_benchmark --queries benchmark_queries.json --out submission.json --limit 10

```

---
