from django.contrib import admin
from django.utils.html import format_html
from .models import Brand, HeroSlide, HomepageSettings, Project, Solution, Statistic, Testimonial


@admin.register(HomepageSettings)
class HomepageSettingsAdmin(admin.ModelAdmin):
    list_display = ("hero_heading", "is_active", "display_order")
    list_editable = ("is_active", "display_order")
    search_fields = ("hero_heading", "hero_subheading")


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


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_featured", "is_active", "display_order")
    list_editable = ("is_featured", "is_active", "display_order")
    search_fields = ("title", "location", "category")
    list_filter = ("is_featured", "is_active")


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "website", "is_featured", "is_active", "display_order")
    list_editable = ("is_featured", "is_active", "display_order")
    search_fields = ("name",)
    list_filter = ("is_featured", "is_active")


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "business", "rating", "is_active", "display_order")
    list_editable = ("is_active", "display_order")
    search_fields = ("customer_name", "business", "review")
