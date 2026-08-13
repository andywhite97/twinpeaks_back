from django.db.models import Case, IntegerField, Q, When
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


class RelatedProductListView(ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        product = Product.objects.filter(is_active=True, slug=self.kwargs["slug"]).first()
        if not product:
            return Product.objects.none()

        matches = Q()
        priority = []
        if product.category_id:
            matches |= Q(category_id=product.category_id)
            priority.append(When(category_id=product.category_id, then=0))
        if product.brand_id:
            matches |= Q(brand_id=product.brand_id)
            priority.append(When(brand_id=product.brand_id, then=1))
        if not priority:
            return Product.objects.none()

        return Product.objects.filter(matches, is_active=True).exclude(pk=product.pk).select_related("brand", "category").prefetch_related("images").annotate(
            relevance=Case(*priority, default=2, output_field=IntegerField())
        ).order_by("relevance", "-created_at")[:8]


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
