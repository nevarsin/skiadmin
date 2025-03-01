from django.urls import path
from . import views

urlpatterns = [
    path("", views.list_associates, name="list_associates"),
    path("<int:pk>/", views.edit_associates, name="edit_associates"),
    path("add/", views.add_associates, name="add_associates"),
    path("delete/<int:pk>/", views.delete_associates, name="delete_associates"),

]
