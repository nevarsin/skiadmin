from django.urls import path
from . import views

urlpatterns = [
    path("", views.list_subscriptions, name="list_subscriptions"),
    path("<int:pk>/", views.edit_subscription, name="edit_subscription"),
    path("add/", views.add_subscription, name="add_subscription"),
    path("delete/<int:pk>/", views.delete_subscription, name="delete_subscription"),
]
