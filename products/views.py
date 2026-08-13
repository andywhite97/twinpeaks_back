from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from homepage.models import Brand
from .models import Product, ProductCategory
from .serializers import ProductBrandSerializer, ProductCategorySerializer, ProductSerializer


class ProductPagination(PageNumberPagination):
    page_size = 9
    page_size_query_param = "page_size"
    max_page_size = 24


class ProductListView(ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    pagination_class = ProductPagination

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).select_related("brand", "category").prefetch_related("images")
        if self.request.query_params.get("featured") == "true":
            queryset = queryset.filter(is_featured=True)
        if category_slug := self.request.query_params.get("category"):
            queryset = queryset.filter(category__slug=category_slug)
        if brand_slug := self.request.query_params.get("brand"):
            queryset = queryset.filter(brand__slug=brand_slug)
        ordering = self.request.query_params.get("sort")
        return {
            "name": queryset.order_by("name"),
            "price_asc": queryset.order_by("price", "name"),
            "price_desc": queryset.order_by("-price", "name"),
        }.get(ordering, queryset)


class ProductDetailView(RetrieveAPIView):
    queryset = Product.objects.filter(is_active=True).select_related("brand", "category").prefetch_related("images")
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"


class ProductCategoryListView(ListAPIView):
    serializer_class = ProductCategorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = ProductCategory.objects.filter(is_active=True)
        if self.request.query_params.get("featured") == "true":
            queryset = queryset.filter(is_featured=True)
        return queryset


class ProductBrandListView(ListAPIView):
    serializer_class = ProductBrandSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Brand.objects.filter(is_active=True, products__is_active=True).distinct().order_by("name")
