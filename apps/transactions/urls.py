from django.urls import path

from . import views

urlpatterns = [
    path("", views.list_transactions, name="list_transactions"),
    path("<int:pk>/", views.transaction_detail, name="transaction_detail"),
    path("<int:pk>/edit", views.edit_transactions, name="edit_transactions"),
    path("add/", views.add_transactions, name="add_transactions"),
    path("delete/<int:pk>/", views.delete_transactions, name="delete_transactions"),
    path("receipt/<int:pk>/", views.generate_receipt, name="receipt"),    
    path("<int:pk>/receipt/send/", views.send_receipt, name="send_receipt"),
]
