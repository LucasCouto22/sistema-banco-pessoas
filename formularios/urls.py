from django.urls import path

from . import views

app_name = "formularios"

urlpatterns = [
    path("", views.formularios_lista, name="formularios_lista"),
    path("novo/", views.formulario_novo, name="formulario_novo"),
    path("<uuid:pk>/editar/", views.formulario_editar, name="formulario_editar"),
    path("<uuid:pk>/excluir/", views.formulario_excluir, name="formulario_excluir"),
    path("<uuid:pk>/visualizar/", views.formulario_visualizar, name="formulario_visualizar"),
    path("variaveis/", views.variaveis_lista, name="variaveis_lista"),
    path("variaveis/novo/", views.variavel_novo, name="variavel_novo"),
    path("variaveis/<uuid:pk>/editar/", views.variavel_editar, name="variavel_editar"),
    path("variaveis/<uuid:pk>/excluir/", views.variavel_excluir, name="variavel_excluir"),
    path("categorias/", views.categorias_lista, name="categorias_lista"),
    path("categorias/novo/", views.categoria_novo, name="categoria_novo"),
    path("categorias/<uuid:pk>/editar/", views.categoria_editar, name="categoria_editar"),
    path("categorias/<uuid:pk>/excluir/", views.categoria_excluir, name="categoria_excluir"),
    path(
        "participacoes/<int:participacao_id>/responder/<uuid:formulario_id>/",
        views.responder_formulario,
        name="responder_formulario",
    ),
]
