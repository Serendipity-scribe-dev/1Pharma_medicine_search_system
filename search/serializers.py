# search/serializers.py
from rest_framework import serializers
from .models import Medicine

class MedicineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicine
        fields = ['id', 'sku_id', 'name', 'manufacturer_name', 'marketer_name',
                  'type', 'price', 'pack_size_label', 'short_composition',
                  'is_discontinued', 'available']
