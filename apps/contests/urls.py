from django.urls import path

from . import views

urlpatterns = [
    path("", views.list_contests, name="list_contests"),
    path("add/", views.add_contest, name="add_contest"),
    path("<int:pk>/edit/", views.edit_contest, name="edit_contest"),
    path("<int:pk>/finalize/", views.finalize_contest, name="finalize_contest"),
    path("<int:pk>/times/", views.edit_times, name="edit_times"),
    path("<int:pk>/end/", views.end_contest, name="end_contest"),
    path("delete/<int:pk>/", views.delete_contest, name="delete_contest"),
    path("report/start/<int:pk>/", views.start_list_pdf, name="start_list_pdf"),
    path("report/results/<int:pk>/", views.results_pdf, name="results_pdf"),
]