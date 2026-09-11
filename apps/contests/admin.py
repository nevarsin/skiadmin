from django.contrib import admin

from .models import Contest, ContestParticipant


class ContestParticipantInline(admin.TabularInline):
    model = ContestParticipant
    extra = 0


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = ("name", "date", "location", "status")
    list_filter = ("status",)
    inlines = [ContestParticipantInline]


admin.site.register(ContestParticipant)