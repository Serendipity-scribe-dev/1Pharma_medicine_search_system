# search/urls.py
from django.urls import path
from .views import PrefixSearchView, SubstringSearchView, FullTextSearchView, FuzzySearchView,search_view,UnifiedSearchView

urlpatterns = [
    path('search/prefix', PrefixSearchView.as_view(), name='search-prefix'),
    path('search/substring', SubstringSearchView.as_view(), name='search-substring'),
    path('search/fulltext', FullTextSearchView.as_view(), name='search-fulltext'),
    path('search/fussy', FuzzySearchView.as_view(), name='search-fuzzy'),
    path("", search_view, name="search"),
     path('unified/', UnifiedSearchView.as_view(), name='search-unified'),
]
