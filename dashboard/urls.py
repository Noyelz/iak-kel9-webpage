from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path(
        "login/",
        LoginView.as_view(
            template_name="dashboard/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("data/", views.warehouse, name="warehouse"),
    path("dashboard/", views.dashboard, name="dashboard"),
]