from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path("", RedirectView.as_view(url="/joint/"), name="home"),
    path("joint/", views.dashboard, {"view_type": "joint"}, name="dashboard_joint"),
    path("individual/", views.dashboard, {"view_type": "individual"}, name="dashboard_individual"),
    path("update-category/", views.update_category, name="update_category"),
    path("update-rule/", views.update_rule, name="update_rule"),
    path("identify-transaction/", views.identify_transaction, name="identify_transaction"),
    path("analyse-spending/", views.analyse_spending, name="analyse_spending"),
]
