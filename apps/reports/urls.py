from django.urls import path
from . import views

urlpatterns = [
    path("", views.select_report, name="select_report"),
    path("<str:type>/", views.generate_report, name="generate_report"),
]
