from django.urls import path

from . import views

app_name = "pessoas"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("exportar/<str:formato>/", views.exportar, name="exportar"),
    path("novo/", views.novo, name="novo"),
    path("wizard/", views.wizard_projeto, name="wizard_projeto"),
    path("wizard/modo/", views.wizard_modo, name="wizard_modo"),
    path("wizard/dados/csv/", views.wizard_dados_csv, name="wizard_dados_csv"),
    path("wizard/dados/csv/modelo/", views.wizard_modelo_csv, name="wizard_modelo_csv"),
    path("wizard/dados/manual/", views.wizard_dados_manual, name="wizard_dados_manual"),
    path("wizard/revisao/", views.wizard_revisao, name="wizard_revisao"),
    path("wizard/cancelar/", views.wizard_cancelar, name="wizard_cancelar"),
    path("cadastro/<str:token>/", views.cadastro_publico, name="cadastro_publico"),
    path("<int:pk>/", views.detalhe, name="detalhe"),
    path("<int:pk>/editar/", views.editar, name="editar"),
    path("<int:pk>/excluir/", views.excluir, name="excluir"),
    path("<int:pk>/aprovar/", views.aprovar, name="aprovar"),
    path("<int:pk>/descartar/", views.descartar, name="descartar"),
    path("<int:pk>/revelar/<str:campo>/", views.revelar_campo, name="revelar_campo"),
]
