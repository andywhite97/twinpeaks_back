from django.contrib import admin
from django.utils.html import format_html
from .models import Brand, HeroSlide, HomepageSettings, Project, ProjectImage, Solution, Statistic, Testimonial


@admin.register(HomepageSettings)
class HomepageSettingsAdmin(admin.ModelAdmin):
    list_display = ("hero_heading", "is_active", "display_order")
    list_editable = ("is_active", "display_order")
    search_fields = ("hero_heading", "hero_subheading")
    list_filter = ("is_active",)


@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ("title", "button_text", "is_active", "display_order")
    list_editable = ("is_active", "display_order")
    search_fields = ("title",)


@admin.register(Solution)
class SolutionAdmin(admin.ModelAdmin):
    list_display = ("title", "icon", "is_active", "display_order")
    list_editable = ("is_active", "display_order")
    search_fields = ("title", "description")


@admin.register(Statistic)
class StatisticAdmin(admin.ModelAdmin):
    list_display = ("label", "value", "suffix", "is_active", "display_order")
    list_editable = ("is_active", "display_order")
    search_fields = ("label",)


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


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("logo_preview", "name", "slug", "is_featured", "is_active", "display_order")
    list_editable = ("is_featured", "is_active", "display_order")
    search_fields = ("name",)
    list_filter = ("is_featured", "is_active")
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Logo")
    def logo_preview(self, obj):
        return format_html('<img src="{}" style="height: 36px; width: 72px; object-fit: contain;" />', obj.logo.url) if obj.logo else "—"


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("photo_preview", "customer_name", "business", "rating", "is_active", "display_order")
    list_editable = ("is_active", "display_order")
    search_fields = ("customer_name", "business", "review")

    @admin.display(description="Photo")
    def photo_preview(self, obj):
        return format_html('<img src="{}" style="height: 36px; width: 36px; object-fit: cover; border-radius: 50%;" />', obj.photo.url) if obj.photo else "—"
