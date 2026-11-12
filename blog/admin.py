from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils.html import format_html
from .models import BlogCategory, BlogPost


@admin.register(BlogCategory)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_order')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(BlogPost)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'category', 'is_featured', 'published_at')
    list_filter = ('status', 'category', 'is_featured')
    search_fields = ('title', 'excerpt')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('solutions',)
    readonly_fields = ('preview_link', 'created_at', 'updated_at')
    fieldsets = (
        ('Article', {'fields': ('title', 'slug', 'excerpt', 'body', 'preview_link')}),
        ('Image and attribution', {'fields': ('cover_image', 'cover_alt', 'author_name')}),
        ('Organisation', {'fields': ('category', 'solutions', 'is_featured')}),
        ('Publication', {'fields': ('status', 'published_at', 'created_at', 'updated_at')}),
    )

    class Media:
        js = ('blog/editor.js',)
        css = {'all': ('blog/editor.css',)}

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    def preview_link(self, obj):
        if not obj or not obj.pk:
            return 'Save your draft to preview it.'
        return format_html('<a href="{}" target="_blank" rel="noopener">Preview saved article</a>', reverse('admin:blog_post_preview', args=[obj.pk]))

    def get_urls(self):
        return [path('<int:pk>/preview/', self.admin_site.admin_view(self.preview), name='blog_post_preview')] + super().get_urls()

    def preview(self, request, pk):
        post = get_object_or_404(BlogPost, pk=pk)
        if not self.has_view_or_change_permission(request, post):
            raise PermissionDenied
        response = render(request, 'blog/preview.html', {'post': post})
        response['Cache-Control'] = 'no-store'
        response['X-Robots-Tag'] = 'noindex, nofollow'
        return response
