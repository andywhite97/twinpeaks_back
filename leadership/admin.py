from django.contrib import admin
from .models import Leader


@admin.register(Leader)
class LeaderAdmin(admin.ModelAdmin):
    list_display = ("name", "role")
    search_fields = ("name", "role")
