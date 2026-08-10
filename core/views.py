from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from accounts.permissions import requer_permissao
from participacoes.models import Participacao
from pessoas.models import Participante
from projetos.models import Projeto

from .dashviz import (
    COR_ETAPA,
    COR_SITUACAO,
    construir_barras_horizontais,
    construir_donut,
    dados_participantes_dashboard,
)


@login_required
def home(request):
    contexto = {}

    if request.user.tem_permissao("participantes.ver"):
        participantes = Participante.objects.all()
        total = participantes.count()
        contexto.update(
            {
                "total_participantes": total,
                "total_aprovados": participantes.filter(situacao=Participante.Situacao.APROVADO).count(),
                "total_pendentes": participantes.filter(situacao=Participante.Situacao.PENDENTE).count(),
                "total_descartados": participantes.filter(situacao=Participante.Situacao.DESCARTADO).count(),
            }
        )

        if total:
            contexto["dash_participantes_json"] = dados_participantes_dashboard(participantes)

            situacao_itens = [
                {"label": label, "count": participantes.filter(situacao=valor).count(), "cor": COR_SITUACAO[valor]}
                for valor, label in Participante.Situacao.choices
            ]
            contexto["donut_situacao"] = construir_donut(situacao_itens, str(total), "participantes")

    if request.user.tem_permissao("projetos.ver"):
        contexto["total_projetos"] = Projeto.objects.exclude(status=Projeto.Status.CONCLUIDO).count()

    if request.user.tem_permissao("participacoes.ver"):
        participacoes = Participacao.objects.all()
        contexto["total_participacoes"] = participacoes.count()
        etapa_itens = [
            {
                "label": label,
                "count": participacoes.filter(etapa=valor).count(),
                "cor": COR_ETAPA[valor],
            }
            for valor, label in Participacao.Etapa.choices
        ]
        contexto["barras_pipeline"] = construir_barras_horizontais(etapa_itens)

    return render(request, "core/home.html", contexto)


@login_required
@requer_permissao("participantes.ver")
def dashboard_segmento(request):
    contexto = {}
    participantes = Participante.objects.all()
    if participantes.exists():
        contexto["dash_participantes_json"] = dados_participantes_dashboard(participantes)
    return render(request, "core/dashboard_segmento.html", contexto)
