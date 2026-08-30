from django.urls import path
from .views import MetaCatalogFeedView, ProductBrandListView, ProductCategoryListView, ProductListView, ProductDetailView, RelatedProductListView

urlpatterns = [
    path("meta/catalog-feed.csv", MetaCatalogFeedView(), name="meta-catalog-feed"),
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<slug:slug>/related/", RelatedProductListView.as_view(), name="related-product-list"),
    path("products/<slug:slug>/", ProductDetailView.as_view(), name="product-detail"),
    path("categories/", ProductCategoryListView.as_view(), name="product-category-list"),
    path("brands/", ProductBrandListView.as_view(), name="product-brand-list"),
]
