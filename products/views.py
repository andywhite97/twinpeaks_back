from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from .models import Product, ProductCategory
from .serializers import ProductCategorySerializer, ProductSerializer


class ProductPagination(PageNumberPagination):
    page_size = 9
    page_size_query_param = "page_size"
    max_page_size = 24


class ProductListView(ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    pagination_class = ProductPagination

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).select_related("brand", "category")
        if self.request.query_params.get("featured") == "true":
            queryset = queryset.filter(is_featured=True)
        if category_slug := self.request.query_params.get("category"):
            queryset = queryset.filter(category__slug=category_slug)
        if brand_slug := self.request.query_params.get("brand"):
            queryset = queryset.filter(brand__slug=brand_slug)
        return queryset


class ProductDetailView(RetrieveAPIView):
    queryset = Product.objects.filter(is_active=True).select_related("brand", "category")
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
