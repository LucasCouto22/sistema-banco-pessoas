from django.urls import path

from . import views

app_name = "projetos"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("novo/", views.novo, name="novo"),
    path("<int:pk>/", views.detalhe, name="detalhe"),
    path("<int:pk>/editar/", views.editar, name="editar"),
    path("<int:pk>/excluir/", views.excluir, name="excluir"),
    path("<int:projeto_pk>/perfis/novo/", views.perfil_novo, name="perfil_novo"),
    path("perfis/<int:pk>/", views.perfil_detalhe, name="perfil_detalhe"),
    path("perfis/<int:pk>/editar/", views.perfil_editar, name="perfil_editar"),
    path("perfis/<int:pk>/excluir/", views.perfil_excluir, name="perfil_excluir"),
    path("perfis/<int:pk>/associar-lote/", views.perfil_associar_lote, name="perfil_associar_lote"),
    path(
        "perfis/<int:pk>/associar-lote/modelo/",
        views.perfil_associar_lote_modelo,
        name="perfil_associar_lote_modelo",
    ),
]
