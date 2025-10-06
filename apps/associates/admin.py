from django.contrib import admin
from import_export import resources, widgets
from import_export.admin import ImportExportModelAdmin
from import_export.fields import Field

from .models import Associate


class AssociateAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'membership_type', 'card_sent')  # Fields to show in list view
    search_fields = ('first_name', 'last_name', 'email')  # Fields to search in admin

class AssociateResource(resources.ModelResource):
    expiration_date = Field(attribute='expiration_date', column_name='expiration_date', widget=widgets.DateWidget(format='%d/%m/%y')) 
    birth_date = Field(attribute='birth_date', column_name='birth_date', widget=widgets.DateWidget(format='%d/%m/%y')) 
    joined_date = Field(attribute='joined_date', column_name='joined_date', widget=widgets.DateWidget(format='%d/%m/%y')) 
    class Meta:
        model = Associate  # or 'core.Book'
        exclude = ('id', 'created_at')
        import_id_fields = [] 
  

# Register for Admin import/export
@admin.register(Associate)
class AssociateAdmin(ImportExportModelAdmin):
    resource_classes = [AssociateResource]
    

# Register the model with the admin interface
#admin.site.register(Associate)