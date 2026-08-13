from rest_framework import serializers
from homepage.models import Brand
from .models import Product, ProductCategory


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ("id", "name", "slug", "image", "description", "is_featured", "display_order")


class ProductBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ("id", "name", "slug", "logo")


class ProductSerializer(serializers.ModelSerializer):
    category = ProductCategorySerializer(read_only=True)
    brand = ProductBrandSerializer(read_only=True)
    stock_status = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "price",
            "sale_price",
            "image",
            "category",
            "brand",
            "stock_quantity",
            "stock_status",
            "rating",
            "installation_available",
            "is_featured",
            "created_at",
        )

        read_only_fields = ("id", "created_at")

    def get_stock_status(self, obj):
        return "in_stock" if obj.stock_quantity > 0 else "out_of_stock"
