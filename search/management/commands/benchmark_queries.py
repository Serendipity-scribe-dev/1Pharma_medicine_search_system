# search/management/commands/benchmark_queries.py
import json
import time
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection
from search.models import Medicine

class Command(BaseCommand):
    help = "Run fixed queries from benchmark_queries.json and produce submission.json plus timing."

    def add_arguments(self, parser):
        parser.add_argument('--queries', default='benchmark_queries.json', help='Path to queries JSON')
        parser.add_argument('--limit', type=int, default=10, help='Top-K names to include per query')
        parser.add_argument('--out', default='submission.json', help='Output submission file')

    def handle(self, *args, **options):
        qpath = options['queries']
        limit = options['limit']
        outpath = options['out']

        with open(qpath, 'r', encoding='utf8') as f:
            qset = json.load(f)

        results_map = {}
        timing = {}
        for item in qset:
            qid = str(item['id'])
            q = item['q']
            # measure single-run latency (ORM direct)
            t0 = time.perf_counter()
            qs = (Medicine.objects
                  .annotate(sim=__import__('django.contrib.postgres.search', fromlist=['TrigramSimilarity']).TrigramSimilarity('name', q))
                  .filter(name__icontains=q)
                  .order_by('-sim', 'name')[:limit])
            names = list(qs.values_list('name', flat=True))
            t1 = time.perf_counter()
            elapsed_ms = (t1 - t0) * 1000.0
            results_map[qid] = names
            timing[qid] = round(elapsed_ms, 2)
            self.stdout.write(self.style.SUCCESS(f"Q {qid}: '{q}' -> {len(names)} results in {elapsed_ms:.2f} ms"))

        # Build submission.json in required format:
        submission_template = {"results": results_map}
        with open(outpath, 'w', encoding='utf8') as f:
            json.dump(submission_template, f, indent=2, ensure_ascii=False)

        # Save a small timings file
        with open('benchmark_timing.json', 'w', encoding='utf8') as f:
            json.dump(timing, f, indent=2)

        self.stdout.write(self.style.SUCCESS(f"Wrote submission to {outpath} and timing to benchmark_timing.json"))
