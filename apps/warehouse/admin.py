from django.contrib import admin

from .models import SkipassUsage


@admin.register(SkipassUsage)
class SkipassUsageAdmin(admin.ModelAdmin):
    list_display = ("date", "associate", "article", "quantity")
    list_filter = ("date", "article")
    search_fields = ("associate__first_name", "associate__last_name")
    date_hierarchy = "date"
