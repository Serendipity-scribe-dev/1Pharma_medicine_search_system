# Medicine Search System (Django + PostgreSQL)

A high-performance medicine search engine built with Django and PostgreSQL, supporting multiple search modes: prefix, substring, full-text, and fuzzy search.

---

## Features

- Prefix Search – Fast lookups for queries matching the start of medicine names.

- Substring Search – Flexible search for queries appearing anywhere in the name.

- Full-text Search – PostgreSQL text search across medicine names.

- Fuzzy Search – Handles typos/misspellings using trigram similarity.

- Django REST API – Search endpoints exposed via Django views.

- Benchmarking – Evaluate latency, throughput, and query performance using provided dataset.

---

## Setup

1. Clone Repository

```bash
git clone https://github.com/Serendipity-scribe-dev/1Pharma_medicine_search_system.git
cd medicine-search-django

```

2. Virtual Enviroment

```bash
python3 -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

3. Install Dependencies

```bash
pip install -r requirements.txt
```

4. Setup PostgreSql:

Create DB and import schema:

```bash
psql -U postgres -d medicines -f schema.sql
```

Load dataset:

```bash
python import_data.py
```

5. Run Migrations

```bash
python manage.py migrate
```

6. Start Development Server

```bash
python manage.py runserver
```

---

## API Endpoints

Base URL/ Frontend : http://127.0.0.1:8000/search/

1. Prefix Search

```bash
GET /search/prefix?q=Parac
```

2. Substring Search

```bash
GET /search/substring?q=cin
```

3. Full text Search

```bash
GET /search/fulltext?q=cancer
```

4. Fuzzy Search

```bash
GET /search/fuzzy?q=paracetmol
```

---

## Benchmarking

Run benchmark with provided query set:

```bash
python manage.py run_benchmark --queries benchmark_queries.json --out submission.json --limit 10
```

## Benchmark details are documented in [Benchmark Report](benchmark.md)
