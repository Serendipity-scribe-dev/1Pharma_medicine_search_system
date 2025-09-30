from django.shortcuts import render

# Create your views here.
# search/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models.functions import Lower
from django.db.models import F,Q
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.contrib.postgres.search import TrigramSimilarity
from .models import Medicine
from .serializers import MedicineSerializer

DEFAULT_LIMIT = 20

class PrefixSearchView(APIView):
    def get(self, request):
        q = request.GET.get('q', '').strip()
        limit = int(request.GET.get('limit', DEFAULT_LIMIT))
        if not q:
            return Response([], status=status.HTTP_200_OK)
        # Use lower(name) functional match to use the btree index
        lower_q = q.lower()
        qs = (Medicine.objects
              .annotate(lower_name=Lower('name'))
              .filter(lower_name__startswith=lower_q)
              .order_by('lower_name')[:limit])
        return Response(MedicineSerializer(qs, many=True).data)

class SubstringSearchView(APIView):
    def get(self, request):
        q = request.GET.get('q', '').strip()
        limit = int(request.GET.get('limit', DEFAULT_LIMIT))
        if not q:
            return Response([], status=status.HTTP_200_OK)
        # ILIKE '%q%' + order by trigram similarity
        qs = (Medicine.objects
              .annotate(sim=TrigramSimilarity('name', q))
              .filter(name__icontains=q)
              .order_by('-sim', 'name')[:limit])
        return Response(MedicineSerializer(qs, many=True).data)

class FullTextSearchView(APIView):
    def get(self, request):
        q = request.GET.get('q', '').strip()
        limit = int(request.GET.get('limit', DEFAULT_LIMIT))
        if not q:
            return Response([], status=status.HTTP_200_OK)
        query = SearchQuery(q, config='simple')  # 'simple' avoids stemming; choose 'english' if needed
        # Use the materialized tsvector column name_tsv (populated by trigger) for best performance
        qs = (Medicine.objects
              .annotate(rank=SearchRank(F('name_tsv'), query))
              .filter(name_tsv__search=q)
              .order_by('-rank')[:limit])
        return Response(MedicineSerializer(qs, many=True).data)

class FuzzySearchView(APIView):
    def get(self, request):
        q = request.GET.get('q', '').strip()
        limit = int(request.GET.get('limit', DEFAULT_LIMIT))
        threshold = float(request.GET.get('threshold', 0.3))  # tuneable
        if not q:
            return Response([], status=status.HTTP_200_OK)
        qs = (Medicine.objects
              .annotate(sim=TrigramSimilarity('name', q))
              .filter(sim__gte=threshold)
              .order_by('-sim')[:limit])
        return Response(MedicineSerializer(qs, many=True).data)
    

def search_view(request):
    query = request.GET.get("q", "")
    search_type = request.GET.get("type", "fulltext")  # default fulltext
    results = []

    if query:
        if search_type == "prefix":
            results = Medicine.objects.filter(name__istartswith=query)[:20]

        elif search_type == "substring":
            results = Medicine.objects.filter(name__icontains=query)[:20]

        elif search_type == "fuzzy":
            results = (
                Medicine.objects
                .annotate(similarity=TrigramSimilarity("name", query))
                .filter(similarity__gt=0.2)
                .order_by("-similarity")[:20]
            )

        else:  # fulltext
            sq = SearchQuery(query)
            results = (
                Medicine.objects
                .annotate(rank=SearchRank(F("name_tsv"), sq))
                .filter(name_tsv=sq)
                .order_by("-rank")[:20]
            )

    return render(request, "search.html", {
        "results": results,
        "query": query,
        "search_type": search_type,
    })

# def unified_search_view(request):
#     query = request.GET.get("q", "").strip()
#     results = []

#     if query:
#         # Full-text search
#         sq = SearchQuery(query)
#         fulltext_filter = Q(name_tsv=sq)

#         # Prefix search
#         prefix_filter = Q(name__istartswith=query)

#         # Substring search
#         substring_filter = Q(name__icontains=query)

#         # Fuzzy search using trigram similarity operator
#         fuzzy_filter = Q(name__trigram_similar=query)  # automatically fuzzy

#         # Combine all filters
#         combined_filter = fulltext_filter | prefix_filter | substring_filter | fuzzy_filter

#         # Annotate relevance (rank + similarity)
#         results = (
#             Medicine.objects
#             .filter(combined_filter)
#             .annotate(
#                 rank=SearchRank(F("name_tsv"), sq),
#                 similarity=TrigramSimilarity("name", query)
#             )
#             .order_by("-rank", "-similarity")[:20]  # top 20
#         )

#     return render(request, "search.html", {
#         "results": results,
#         "query": query,
#     })
