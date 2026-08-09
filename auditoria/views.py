from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from accounts.permissions import requer_permissao

from .models import RegistroAcesso

Usuario = get_user_model()


@login_required
@requer_permissao("auditoria.ver")
def lista(request):
    registros = RegistroAcesso.objects.select_related("usuario")

    usuario_id = request.GET.get("usuario")
    titular = request.GET.get("titular", "").strip()
    acao = request.GET.get("acao")
    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")

    if usuario_id:
        registros = registros.filter(usuario_id=usuario_id)
    if titular:
        registros = registros.filter(titular__icontains=titular)
    if acao:
        registros = registros.filter(acao=acao)
    if data_inicio:
        registros = registros.filter(quando__date__gte=data_inicio)
    if data_fim:
        registros = registros.filter(quando__date__lte=data_fim)

    return render(
        request,
        "auditoria/lista.html",
        {
            "registros": registros[:500],
            "usuarios": Usuario.objects.order_by("first_name", "username"),
            "acoes": RegistroAcesso.Acao.choices,
            "filtros": {
                "usuario": usuario_id or "",
                "titular": titular,
                "acao": acao or "",
                "data_inicio": data_inicio or "",
                "data_fim": data_fim or "",
            },
        },
    )
