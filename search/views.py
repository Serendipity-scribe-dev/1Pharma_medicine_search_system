from django.shortcuts import render

# Create your views here.
# search/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models.functions import Lower
from django.db.models import F,Q
from django.db.models import F, Q, Case, When, Value, FloatField
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.contrib.postgres.search import TrigramSimilarity
from .models import Medicine
from .serializers import MedicineSerializer
from django.db.models.functions import Length

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
    query = request.GET.get("q", "").strip()
    
    results = []

    if query:
        search_query = SearchQuery(query, config='simple')
        
        # 1. Annotate: Calculate all necessary scores first.
        qs = Medicine.objects.annotate(
            trigram_sim=TrigramSimilarity('name', query), 
            rank=SearchRank(F('name_tsv'), search_query),
            relevance_boost=Case(
                When(name__iexact=query, then=Value(1.0)), 
                When(name__istartswith=query, then=Value(0.9)),
                default=Value(0.0),
                output_field=FloatField()
            )
        )
        
        # 2. Build the Comprehensive Filter (Single .filter() call with OR logic)
        # This ensures we include results if they satisfy ANY of the following:
        
        combined_filter = (
            # A) Full-Text Search Match
            Q(name_tsv=search_query) | 
            
            # B) Substring/Prefix Match (covers "Ava" in "Avastin")
            Q(name__icontains=query) | 
            
            # C) Fuzzy Match (Covers "Avastn" using the annotated similarity score)
            Q(trigram_sim__gte=0.15)  # <-- Use a low threshold (0.1) for max typo tolerance
        )
        
        # 3. Apply Filter and Ordering
        results = qs.filter(
            combined_filter
        ).order_by(
            '-relevance_boost', 
            Length('name'),
            '-rank', 
            '-trigram_sim', 
            'name' 
        )[:20]
        
    return render(request, "search.html", {
        "results": results,
        "query": query,
    })

class UnifiedSearchView(APIView):
    def get(self, request):
        q = request.GET.get('q', '').strip()
        limit = int(request.GET.get('limit', DEFAULT_LIMIT))
        
        if not q:
            # Return an empty list if the query is empty
            return Response([], status=status.HTTP_200_OK)

        # --- Base Search Components ---
        
        # 1. Full-text Search (Requires 'name_tsv' on the model)
        # Use a more sophisticated config like 'english' if needed, but 'simple' is fast.
        search_query = SearchQuery(q, config='simple')
        fulltext_filter = Q(name_tsv__search=search_query)

        # 2. Prefix Search (Case-insensitive start)
        prefix_filter = Q(name__icontains=q) # Use icontains and let ranking handle it, or istartswith for strict prefix
        # Alternative strict prefix filter: Q(name__istartswith=q)
        
        # 3. Fuzzy Search (Trigram Similarity)
        # We'll use a relatively low threshold and let the similarity score handle the ranking.
        # Note: TrigramSimilarity is an annotation, so we just use the final filter.
        # A filter on `name__trigram_similar` can also be used, but let's keep it simple for now and rely on annotation.

        # 4. Keyword Match (Exact case-insensitive match for top relevance)
        exact_match_filter = Q(name__iexact=q)
        
        # Combine all filters with OR. This ensures a broad range of potential matches are included.
        # The combination is: (Exact OR Prefix OR FullText) and rely on Trigram for fuzzy
        # Note: `name__icontains` covers prefix and substring. We use it to ensure broad results.
        combined_filter = Q(name__icontains=q) | fulltext_filter 

        # --- Annotation and Ranking ---

        # Annotate with PostgreSQL Trigram Similarity and Full-Text Search Rank
        qs = Medicine.objects.annotate(
            # Calculate Trigram Similarity (for fuzzy and general relevance)
            trigram_sim=TrigramSimilarity('name', q),
            
            # Calculate Full-Text Search Rank (for relevance based on text weight/position)
            # Use 'rank' as a final rank component
            rank=SearchRank(F('name_tsv'), search_query),
            
            # Custom relevance boost using Case/When:
            relevance_boost=Case(
                # Highest boost for an exact match (case-insensitive)
                When(name__iexact=q, then=Value(1.0)), 
                # Good boost for a strict prefix match
                When(name__istartswith=q, then=Value(0.5)),
                default=Value(0.0),
                output_field=FloatField()
            )
        ).filter(
            # Filter to include matches from combined logic (full-text OR substring/prefix/exact)
            combined_filter, 
            # AND filter: Only include results that are above a minimum fuzzy threshold 
            # (optional, but good for filtering out irrelevant trigram noise)
            trigram_sim__gt=0.2 
        ).order_by(
            # Final ordering logic:
            # 1. Exact/Prefix matches get priority
            '-relevance_boost', 
            # 2. Results are ordered by FTS Rank
            '-rank', 
            # 3. Then by Trigram Similarity (fuzzy score)
            '-trigram_sim', 
            # 4. Fallback to alphabetical order
            'name' 
        )[:limit]
        
        # --- Response ---
        return Response(MedicineSerializer(qs, many=True).data)