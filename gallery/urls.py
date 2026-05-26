from django.urls import path
from .views import GalleryItemDetailView, GalleryItemListView


urlpatterns = [
    path("gallery/", GalleryItemListView.as_view(), name="gallery-list"),
    path("gallery/<slug:slug>/", GalleryItemDetailView.as_view(), name="gallery-detail"),
]
