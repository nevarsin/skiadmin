from django.urls import path

from . import views

urlpatterns = [
    path("", views.plan_view, name="warehouse_plan"),
    path("undo/<str:day>/", views.undo_view, name="warehouse_undo"),
]
