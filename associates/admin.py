from django.contrib import admin
from .models import Associate

class AssociateAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'membership_type', 'card_sent')  # Fields to show in list view
    search_fields = ('first_name', 'last_name', 'email')  # Fields to search in admin


# Register the model with the admin interface
admin.site.register(Associate)