from django.contrib import admin
from django.utils.html import format_html
from .models import Product, ProductCategory


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("image_preview", "name", "category", "price", "sale_price", "stock_quantity", "is_featured", "is_active", "created_at")
    list_filter = ("is_active", "is_featured", "category", "created_at")
    list_editable = ("is_featured", "is_active")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Image")
    def image_preview(self, obj):
        return format_html('<img src="{}" style="height: 42px; width: 64px; object-fit: cover; border-radius: 4px;" />', obj.image.url) if obj.image else "—"


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_featured", "is_active", "display_order")
    list_editable = ("is_featured", "is_active", "display_order")
    list_filter = ("is_featured", "is_active")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
