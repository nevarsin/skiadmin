from django.urls import path
from . import views

urlpatterns = [
    path("", views.associate_list, name="associates_list"),
    path("<int:pk>/", views.associate_detail, name="associates_detail"),
    path("add/", views.add_associate, name="add_associate"),
    path("delete/<int:pk>/", views.delete_associate, name="delete_associate"),
]
