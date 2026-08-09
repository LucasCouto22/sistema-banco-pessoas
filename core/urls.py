from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("segmento/", views.dashboard_segmento, name="dashboard_segmento"),
]
