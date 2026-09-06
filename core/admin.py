from django.contrib import admin
from .models import CompanyProfile

@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "tagline", "email", "phone")
    fieldsets = (
        (None, {"fields": ("name", "logo", "tagline")} ),
        ("Content", {"fields": ("overview", "vision", "mission")}),
        ("Contact details", {"fields": ("email", "phone", "whatsapp", "address", "business_hours")} ),
        ("Social Links", {"fields": ("facebook", "twitter", "instagram", "linkedin")} ),
        ("Footer", {"fields": ("copyright_text",)}),
    )
