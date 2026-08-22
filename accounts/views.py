import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .emails import enviar_email_novo_usuario
from .forms import PerfilForm, PreferenciaAvisosForm, TrocarSenhaForm, UsuarioCreateForm, UsuarioEditForm
from .models import AvisoDispensado, NivelPermissao, Permissao, PreferenciaAvisos, TIPOS_AVISO, Usuario
from .permissions import requer_permissao

logger = logging.getLogger(__name__)


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    pass


class ResetarSenhaView(auth_views.PasswordResetView):
    """"Esqueci minha senha" — tela pública que pede o e-mail e dispara o
    link de redefinição. Reaproveita todo o mecanismo do Django
    (`PasswordResetForm`), só troca os templates (tela + e-mail) pro
    layout/marca do Qualy Vortice."""

    template_name = "accounts/senha_resetar.html"
    email_template_name = "accounts/email/senha_resetar.txt"
    html_email_template_name = "accounts/email/senha_resetar.html"
    subject_template_name = "accounts/email/senha_resetar_assunto.txt"
    success_url = reverse_lazy("accounts:senha_resetar_enviado")

    def form_valid(self, form):
        # `form.save()` (chamado dentro do `form_valid` da view do Django)
        # manda o e-mail de verdade — se o backend de e-mail recusar (ex.:
        # domínio sandbox do Mailgun, destinatário fora da lista de
        # autorizados), isso levantava um erro 500 puro pra quem só queria
        # redefinir a senha. Trata como falha não-bloqueante: loga o motivo
        # de verdade (pra quem administra o sistema investigar) e segue pra
        # tela de "enviado" do mesmo jeito — não revela se o e-mail existe
        # ou não, mesma lógica de segurança que o Django já usa aqui.
        try:
            return super().form_valid(form)
        except Exception:
            logger.exception("Falha ao enviar e-mail de redefinição de senha")
            messages.warning(
                self.request,
                "Não consegui confirmar o envio do e-mail agora — se o problema persistir, "
                "avise um administrador do sistema.",
            )
            return redirect(self.success_url)


class ResetarSenhaEnviadoView(auth_views.PasswordResetDoneView):
    template_name = "accounts/senha_resetar_enviado.html"


class ResetarSenhaConfirmarView(auth_views.PasswordResetConfirmView):
    template_name = "accounts/senha_resetar_confirmar.html"
    success_url = reverse_lazy("accounts:senha_resetar_completo")


class ResetarSenhaCompletoView(auth_views.PasswordResetCompleteView):
    template_name = "accounts/senha_resetar_completo.html"


@login_required
@requer_permissao("usuarios.gerenciar")
def usuarios_lista(request):
    usuarios = Usuario.objects.all().order_by("first_name", "username")
    # "Reenviar e-mail" só aparece pra conta criada há menos de 7 dias — depois
    # disso, o e-mail de boas-vindas original perde o sentido (a pessoa já
    # deve ter entrado com a senha provisória ou já trocou pela própria).
    corte_reenvio_email = timezone.now() - timedelta(days=7)
    return render(
        request,
        "accounts/usuarios_lista.html",
        {"usuarios": usuarios, "corte_reenvio_email": corte_reenvio_email},
    )


@login_required
@requer_permissao("usuarios.gerenciar")
def usuario_novo(request):
    if request.method == "POST":
        form = UsuarioCreateForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            messages.success(request, f"Usuário {usuario.username} criado com sucesso.")
            if usuario.email:
                if enviar_email_novo_usuario(usuario, request):
                    messages.info(request, f"E-mail de boas-vindas enviado para {usuario.email}.")
                else:
                    messages.warning(
                        request,
                        f"Não consegui enviar o e-mail de boas-vindas para {usuario.email} "
                        "(o usuário já foi criado normalmente).",
                    )
            return redirect("accounts:usuarios_lista")
    else:
        form = UsuarioCreateForm()
    return render(request, "accounts/usuario_form.html", {"form": form})


@login_required
@requer_permissao("usuarios.gerenciar")
def usuario_editar(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == "POST":
        form = UsuarioEditForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, f"Usuário {usuario.username} atualizado.")
            return redirect("accounts:usuarios_lista")
    else:
        form = UsuarioEditForm(instance=usuario)
    return render(request, "accounts/usuario_form.html", {"form": form, "titulo": f"Editar {usuario.username}"})


@login_required
@requer_permissao("usuarios.excluir")
def usuario_excluir(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if usuario.pk == request.user.pk:
        messages.error(request, "Você não pode excluir seu próprio usuário.")
        return redirect("accounts:usuarios_lista")
    if request.method == "POST":
        nome = usuario.username
        usuario.delete()
        messages.success(request, f"Usuário {nome} excluído.")
        return redirect("accounts:usuarios_lista")
    return render(request, "accounts/usuario_excluir.html", {"usuario": usuario})


@login_required
@requer_permissao("usuarios.gerenciar")
@require_POST
def usuario_reenviar_email(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if not usuario.email:
        messages.error(request, f"{usuario.username} não tem e-mail cadastrado.")
    elif enviar_email_novo_usuario(usuario, request):
        messages.success(request, f"E-mail de criação de conta reenviado para {usuario.email}.")
    else:
        messages.warning(
            request, f"Não consegui reenviar o e-mail para {usuario.email} (tente de novo em instantes)."
        )
    return redirect("accounts:usuarios_lista")


@login_required
@requer_permissao("permissoes.gerenciar")
def painel_permissoes(request):
    if request.method == "POST":
        for permissao in Permissao.objects.all():
            for nivel, _ in Usuario.Nivel.choices:
                campo = f"perm_{nivel}_{permissao.id}"
                concedida = campo in request.POST
                NivelPermissao.objects.update_or_create(
                    nivel=nivel, permissao=permissao, defaults={"concedida": concedida}
                )
        messages.success(request, "Matriz de permissões atualizada.")
        return redirect("accounts:painel_permissoes")

    niveis = Usuario.Nivel.choices
    concedidas = set(
        NivelPermissao.objects.filter(concedida=True).values_list("nivel", "permissao_id")
    )

    grupos = {}
    for permissao in Permissao.objects.all():
        linha = {
            "permissao": permissao,
            "checks": [
                {"nivel": nivel, "label": label, "marcado": (nivel, permissao.id) in concedidas}
                for nivel, label in niveis
            ],
        }
        grupos.setdefault(permissao.grupo, []).append(linha)

    return render(
        request,
        "accounts/painel_permissoes.html",
        {"niveis": niveis, "grupos": grupos},
    )


def _restringir_campos(form, campos_permitidos):
    for campo in list(form.fields):
        if campo not in campos_permitidos:
            form.fields.pop(campo)


@login_required
def meu_perfil(request):
    preferencia = PreferenciaAvisos.para(request.user)
    campos_avisos_visiveis = [
        campo for campo, codigo in TIPOS_AVISO.items() if request.user.tem_permissao(codigo)
    ]

    if request.method == "POST":
        form_perfil = PerfilForm(request.POST, instance=request.user)
        form_avisos = PreferenciaAvisosForm(request.POST, instance=preferencia)
        _restringir_campos(form_avisos, campos_avisos_visiveis)
        if form_perfil.is_valid() and form_avisos.is_valid():
            form_perfil.save()
            form_avisos.save()
            messages.success(request, "Perfil atualizado.")
            return redirect("accounts:meu_perfil")
    else:
        form_perfil = PerfilForm(instance=request.user)
        form_avisos = PreferenciaAvisosForm(instance=preferencia)
        _restringir_campos(form_avisos, campos_avisos_visiveis)

    return render(
        request,
        "accounts/meu_perfil.html",
        {"form_perfil": form_perfil, "form_avisos": form_avisos},
    )


class TrocarSenhaView(auth_views.PasswordChangeView):
    template_name = "accounts/trocar_senha.html"
    form_class = TrocarSenhaForm
    success_url = reverse_lazy("accounts:meu_perfil")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Senha alterada com sucesso.")
        return response


@login_required
@require_POST
def aviso_dispensar(request):
    chave = request.POST.get("chave", "").strip()
    conteudo = request.POST.get("conteudo", "").strip()
    if chave:
        AvisoDispensado.objects.get_or_create(usuario=request.user, chave=chave, conteudo=conteudo)

    destino = request.POST.get("next", "")
    if destino and url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(destino)
    return redirect("core:home")
