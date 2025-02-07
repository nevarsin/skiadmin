from django.urls import path
from . import views

urlpatterns = [
    path("", views.transactions_list, name="transactions_list"),
    path("<int:pk>/", views.transaction_detail, name="transaction_detail"),
    path("<int:pk>/edit", views.edit_transaction, name="edit_transaction"),
    path("add/", views.add_transaction, name="add_transaction"),
    path("delete/<int:pk>/", views.delete_transaction, name="delete_transaction"),
    path("report/", views.generate_report, name="report"), 
]
