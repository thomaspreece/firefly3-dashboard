from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("update-category/", views.update_category, name="update_category"),
]
