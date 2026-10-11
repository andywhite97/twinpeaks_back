from django.contrib import admin
from django.utils.html import format_html
from .models import HomepageSettings, Project, ProjectImage


@admin.register(HomepageSettings)
class HomepageSettingsAdmin(admin.ModelAdmin):
    list_display = ("hero_heading", "is_active", "display_order")
    list_editable = ("is_active", "display_order")
    search_fields = ("hero_heading", "hero_subheading")
    list_filter = ("is_active",)


class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("image_preview", "title", "category", "is_featured", "is_active", "display_order")
    list_editable = ("is_featured", "is_active", "display_order")
    search_fields = ("title", "location", "category")
    list_filter = ("is_featured", "is_active")
    inlines = (ProjectImageInline,)

    @admin.display(description="Image")
    def image_preview(self, obj):
        return format_html('<img src="{}" style="height: 42px; width: 64px; object-fit: cover; border-radius: 4px;" />', obj.image.url) if obj.image else "—"
