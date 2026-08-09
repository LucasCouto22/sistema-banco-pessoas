from django.urls import path

from . import views

app_name = "participacoes"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("kanban/", views.kanban, name="kanban"),
    path("nova/", views.nova, name="nova"),
    path("<int:pk>/avancar/", views.avancar, name="avancar"),
    path("<int:pk>/avaliar/", views.avaliar, name="avaliar"),
]
