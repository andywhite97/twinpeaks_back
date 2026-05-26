from rest_framework import serializers
from .models import GalleryItem


class GalleryItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = GalleryItem
        fields = (
            "id",
            "title",
            "slug",
            "description",
            "image",
            "display_order",
            "created_at",
        )
        read_only_fields = fields
