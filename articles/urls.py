from django.urls import path
from . import views

urlpatterns = [
    path("", views.list_articles, name="list_articles"),
    path("<int:pk>/", views.edit_article, name="edit_article"),
    path("add/", views.add_article, name="add_article"),
    path("delete/<int:pk>/", views.delete_article, name="delete_article"),
    path("<int:pk>/price/", views.get_article_price, name="get_article_price"),

]
