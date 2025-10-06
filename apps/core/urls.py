from django.urls import path

from .views import delete_settings, edit_settings, manage_settings

urlpatterns = [
    path("settings/", manage_settings, name="manage_settings"),
    path("settings/edit/<int:option_id>/", edit_settings, name="edit_settings"),
    path("settings/delete/<int:option_id>/", delete_settings, name="delete_settings"),
]
