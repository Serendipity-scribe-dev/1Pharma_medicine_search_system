import os
import json
from django.core.management.base import BaseCommand
from search.models import Medicine
from django.db import transaction

class Command(BaseCommand):
    help = "Import medicines from JSON files into PostgreSQL"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            help="Path to folder containing JSON files",
            required=True,
        )

    def handle(self, *args, **options):
        path = options["path"]

        if not os.path.exists(path):
            self.stderr.write(self.style.ERROR(f"Path {path} does not exist"))
            return

        files = [f for f in os.listdir(path) if f.endswith(".json")]
        self.stdout.write(f"Found {len(files)} JSON files.")

        for file in files:
            file_path = os.path.join(path, file)
            self.stdout.write(f"Importing {file_path} ...")

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # bulk insert in transactions for speed
            objs = []
            for record in data:
                objs.append(
                    Medicine(
                        id=record.get("id"),
                        sku_id=record.get("sku_id"),
                        name=record.get("name", ""),
                        manufacturer_name=record.get("manufacturer_name"),
                        marketer_name=record.get("marketer_name"),
                        type=record.get("type"),
                        price=record.get("price") or None,
                        pack_size_label=record.get("pack_size_label"),
                        short_composition=record.get("short_composition"),
                        is_discontinued=record.get("is_discontinued", False),
                        available=record.get("available", True),
                    )
                )

            with transaction.atomic():
                Medicine.objects.bulk_create(objs, ignore_conflicts=True, batch_size=5000)

        self.stdout.write(self.style.SUCCESS("✅ Import completed."))
