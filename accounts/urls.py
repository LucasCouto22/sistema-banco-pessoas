from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("senha/resetar/", views.ResetarSenhaView.as_view(), name="senha_resetar"),
    path("senha/resetar/enviado/", views.ResetarSenhaEnviadoView.as_view(), name="senha_resetar_enviado"),
    path(
        "senha/resetar/confirmar/<uidb64>/<token>/",
        views.ResetarSenhaConfirmarView.as_view(),
        name="senha_resetar_confirmar",
    ),
    path("senha/resetar/completo/", views.ResetarSenhaCompletoView.as_view(), name="senha_resetar_completo"),
    path("usuarios/", views.usuarios_lista, name="usuarios_lista"),
    path("usuarios/novo/", views.usuario_novo, name="usuario_novo"),
    path("usuarios/<int:pk>/editar/", views.usuario_editar, name="usuario_editar"),
    path("usuarios/<int:pk>/excluir/", views.usuario_excluir, name="usuario_excluir"),
    path("permissoes/", views.painel_permissoes, name="painel_permissoes"),
    path("perfil/", views.meu_perfil, name="meu_perfil"),
    path("perfil/senha/", views.TrocarSenhaView.as_view(), name="trocar_senha"),
    path("avisos/dispensar/", views.aviso_dispensar, name="aviso_dispensar"),
]
