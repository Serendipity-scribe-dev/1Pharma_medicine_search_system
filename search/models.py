# search/models.py
from django.db import models
from django.contrib.postgres.search import SearchVectorField

class Medicine(models.Model):
    # using dataset 'id' as primary key (text)
    id = models.CharField(max_length=128, primary_key=True)
    sku_id = models.CharField(max_length=128, blank=True, null=True)
    name = models.TextField()
    manufacturer_name = models.TextField(blank=True, null=True)
    marketer_name = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=128, blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    pack_size_label = models.TextField(blank=True, null=True)
    short_composition = models.TextField(blank=True, null=True)
    is_discontinued = models.BooleanField(default=False)
    available = models.BooleanField(default=True)

    # tsvector column (to be populated via trigger)
    name_tsv = SearchVectorField(null=True, blank=True, editable=False)

    class Meta:
        db_table = 'search_medicine'

    def __str__(self):
        return f"{self.name} ({self.id})"

