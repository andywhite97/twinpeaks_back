from django.urls import path
from .views import ProductCategoryListView, ProductListView, ProductDetailView

urlpatterns = [
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<slug:slug>/", ProductDetailView.as_view(), name="product-detail"),
    path("categories/", ProductCategoryListView.as_view(), name="product-category-list"),
]
