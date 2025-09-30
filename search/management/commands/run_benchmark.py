# search/management/commands/run_benchmark.py
import json, time
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import F
from django.contrib.postgres.search import SearchQuery, SearchRank, TrigramSimilarity,SearchVector
from search.models import Medicine

class Command(BaseCommand):
    help = "Run benchmark queries JSON and produce submission.json (format required)."

    def add_arguments(self, parser):
        parser.add_argument('--queries', default='dataset/benchmark_queries.json')
        parser.add_argument('--out', default='dataset/submission.json')
        parser.add_argument('--limit', type=int, default=10)

    def handle(self, *args, **options):
        path = options['queries']
        out = options['out']
        limit = options['limit']

        with open(path, 'r', encoding='utf8') as f:
            qdoc = json.load(f)

        tests = qdoc.get('tests') or qdoc.get('queries') or []
        submission = {"results": {}}
        timings = {}

        for idx, t in enumerate(tests, start=1):
            qid = str(t.get('id', idx))
            qtype = t.get('type')
            q = t.get('query','').strip()
            if not q:
                submission["results"][qid] = []
                continue

            t0 = time.perf_counter()
            if qtype == 'prefix':
                qs = Medicine.objects.annotate(lower_name=F('name')).filter(name__istartswith=q)[:limit]
            elif qtype == 'substring':
                qs = Medicine.objects.annotate(sim=TrigramSimilarity('name', q)).filter(name__icontains=q).order_by('-sim','name')[:limit]
            elif qtype == "fulltext":
                sq = SearchQuery(q)  # ✅ wrap search string in SearchQuery
                qs = (
                    Medicine.objects
                    .annotate(rank=SearchRank(F("name_tsv"), sq))
                    .filter(name_tsv=sq)                # ✅ correct usage
                    .order_by("-rank")[:limit]
                )
            elif qtype == 'fuzzy':
                thr =  float(t.get('threshold', 0.3))
                qs = Medicine.objects.annotate(sim=TrigramSimilarity('name', q)).filter(sim__gte=thr).order_by('-sim','name')[:limit]
            else:
                # fallback: substring
                qs = Medicine.objects.filter(name__icontains=q)[:limit]
            names = list(qs.values_list('name', flat=True))
            t1 = time.perf_counter()
            elapsed_ms = (t1 - t0) * 1000.0
            timings[qid] = round(elapsed_ms, 2)

            # If duplicated qid already exists, append _dupN
            base_qid = qid
            dup = 1
            while qid in submission['results']:
                qid = f"{base_qid}_dup{dup}"
                dup += 1

            submission['results'][qid] = names

            self.stdout.write(self.style.SUCCESS(f"Query [{qtype}] id={qid} q='{q}' -> {len(names)} rows in {elapsed_ms:.2f} ms"))

        with open(out, 'w', encoding='utf8') as f:
            json.dump(submission, f, indent=2, ensure_ascii=False)

        with open('benchmark_timings.json','w',encoding='utf8') as f:
            json.dump(timings, f, indent=2)

        self.stdout.write(self.style.SUCCESS(f"Wrote submission to {out} and timings to benchmark_timings.json"))
