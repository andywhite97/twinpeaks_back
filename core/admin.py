from django.contrib import admin
from .models import CompanyProfile

@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "tagline")
    fieldsets = (
        (None, {"fields": ("name", "tagline")}),
        ("Content", {"fields": ("overview", "vision", "mission")}),
        ("Social Links", {"fields": ("facebook", "twitter", "instagram", "linkedin")}),
    )
