import csv
from io import StringIO
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings
from django.db.models import Case, IntegerField, Q, When
from django.http import HttpResponse
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from homepage.models import Brand
from .models import Product, ProductCategory
from .serializers import ProductBrandSerializer, ProductCategorySerializer, ProductSerializer


def _https_absolute_url(request, url):
    """Return a public HTTPS URL for a storage URL, including local media URLs."""
    absolute_url = request.build_absolute_uri(url)
    parsed_url = urlsplit(absolute_url)
    return urlunsplit(("https", parsed_url.netloc, parsed_url.path, parsed_url.query, parsed_url.fragment))


class MetaCatalogFeedView:
    """Public, read-only Meta Commerce Manager catalog feed."""

    fields = (
        "id",
        "title",
        "description",
        "availability",
        "condition",
        "price",
        "link",
        "image_link",
        "additional_image_link",
        "brand",
        "product_type",
        "sale_price",
    )

    def __call__(self, request):
        products = (
            Product.objects.filter(is_active=True, price__isnull=False, image__isnull=False)
            .exclude(image="")
            .select_related("category", "brand")
            .prefetch_related("images")
        )

        output = StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=self.fields, lineterminator="\n")
        writer.writeheader()
        for product in products:
            additional_images = [
                _https_absolute_url(request, product_image.image.url)
                for product_image in product.images.all()
                if product_image.image
            ]
            writer.writerow(
                {
                    # A slug is a stable, public catalog identifier and does not reveal
                    # the internal database primary key.
                    "id": product.slug,
                    "title": product.name,
                    "description": product.description,
                    "availability": "in stock" if product.stock_quantity > 0 else "out of stock",
                    "condition": "new",
                    "price": f"{product.price:.2f} SZL",
                    "link": f"{settings.META_CATALOG_STOREFRONT_URL}/products/{product.slug}",
                    "image_link": _https_absolute_url(request, product.image.url),
                    # Meta accepts multiple URLs in this column separated by commas.
                    "additional_image_link": ",".join(additional_images),
                    "brand": product.brand.name if product.brand else "",
                    "product_type": product.category.name if product.category else "",
                    "sale_price": f"{product.sale_price:.2f} SZL" if product.sale_price is not None else "",
                }
            )

        response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'inline; filename="meta-catalog-feed.csv"'
        return response


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
