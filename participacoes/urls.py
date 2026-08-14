from django.urls import path

from . import views

app_name = "participacoes"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("exportar/<str:formato>/", views.exportar, name="exportar"),
    path("kanban/", views.kanban, name="kanban"),
    path("<int:pk>/", views.detalhe, name="detalhe"),
    path("nova/", views.nova, name="nova"),
    path("<int:pk>/avancar/", views.avancar, name="avancar"),
    path("<int:pk>/status/", views.mudar_status, name="mudar_status"),
    path("<int:pk>/etapa/", views.mudar_etapa, name="mudar_etapa"),
    path("<int:pk>/avaliar/", views.avaliar, name="avaliar"),
]
