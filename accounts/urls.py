from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("usuarios/", views.usuarios_lista, name="usuarios_lista"),
    path("usuarios/novo/", views.usuario_novo, name="usuario_novo"),
    path("usuarios/<int:pk>/editar/", views.usuario_editar, name="usuario_editar"),
    path("usuarios/<int:pk>/excluir/", views.usuario_excluir, name="usuario_excluir"),
    path("permissoes/", views.painel_permissoes, name="painel_permissoes"),
    path("perfil/", views.meu_perfil, name="meu_perfil"),
    path("perfil/senha/", views.TrocarSenhaView.as_view(), name="trocar_senha"),
    path("avisos/dispensar/", views.aviso_dispensar, name="aviso_dispensar"),
]
