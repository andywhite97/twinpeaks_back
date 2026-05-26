from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from .models import GalleryItem
from .serializers import GalleryItemSerializer


class GalleryPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 36


class GalleryItemListView(ListAPIView):
    queryset = GalleryItem.objects.filter(is_active=True)
    serializer_class = GalleryItemSerializer
    permission_classes = [AllowAny]
    pagination_class = GalleryPagination


class GalleryItemDetailView(RetrieveAPIView):
    queryset = GalleryItem.objects.filter(is_active=True)
    serializer_class = GalleryItemSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"
