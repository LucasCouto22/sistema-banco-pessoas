from django.urls import path

from . import views

app_name = "termos"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("novo/", views.novo, name="novo"),
    path("<int:pk>/", views.detalhe, name="detalhe"),
    path("<int:pk>/nova-versao/", views.nova_versao, name="nova_versao"),
]
