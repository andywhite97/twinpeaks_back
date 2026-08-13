from django import forms
from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from .models import Product, ProductCategory


class MarkdownTextarea(forms.Textarea):
    class Media:
        css = {"all": ("products/markdown_editor.css",)}
        js = ("products/markdown_editor.js",)

    def __init__(self, *args, **kwargs):
        attrs = kwargs.setdefault("attrs", {})
        attrs["class"] = f"{attrs.get('class', '')} markdown-editor".strip()
        attrs.setdefault("rows", 16)
        super().__init__(*args, **kwargs)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("image_preview", "name", "brand", "category", "price", "sale_price", "stock_quantity", "is_featured", "is_active", "created_at")
    list_filter = ("is_active", "is_featured", "brand", "category", "created_at")
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
    formfield_overrides = {
        models.TextField: {"widget": MarkdownTextarea},
    }
