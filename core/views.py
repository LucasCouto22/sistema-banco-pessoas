from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render
from django.utils import timezone

from accounts.permissions import requer_permissao
from participacoes.models import Participacao
from pessoas.models import Participante
from projetos.models import Projeto

FAIXAS_ETARIAS = [
    ("18-24", 18, 24),
    ("25-34", 25, 34),
    ("35-44", 35, 44),
    ("45-54", 45, 54),
    ("55+", 55, 200),
]


def _idade_em(nascimento, hoje):
    anos = hoje.year - nascimento.year
    if (hoje.month, hoje.day) < (nascimento.month, nascimento.day):
        anos -= 1
    return anos


def _grafico_ordenado(queryset, campo, choices):
    """Gráfico de categorias com ordem natural (ex.: faixa de renda, escolaridade,
    etapas do funil) — mantém todas as categorias, mesmo com contagem zero."""
    contagem = {item[campo]: item["total"] for item in queryset.values(campo).annotate(total=Count("id"))}
    labels = [label for _, label in choices]
    valores = [contagem.get(valor, 0) for valor, _ in choices]
    return {"labels": labels, "valores": valores}


def _grafico_top(queryset, campo, limite=8, choices=None):
    """Gráfico de categorias sem ordem natural (ex.: UF, cidade, gênero) — mostra as
    N mais frequentes, maior para menor."""
    mapa = dict(choices) if choices else {}
    contagem = (
        queryset.exclude(**{campo: ""}).values(campo).annotate(total=Count("id")).order_by("-total")[:limite]
    )
    labels = [mapa.get(item[campo], item[campo]) for item in contagem]
    valores = [item["total"] for item in contagem]
    return {"labels": labels, "valores": valores}


def _grafico_faixa_etaria(participantes):
    hoje = timezone.localdate()
    baldes = dict.fromkeys((rotulo for rotulo, _, _ in FAIXAS_ETARIAS), 0)
    for nascimento in participantes.values_list("data_nascimento", flat=True):
        idade = _idade_em(nascimento, hoje)
        for rotulo, minimo, maximo in FAIXAS_ETARIAS:
            if minimo <= idade <= maximo:
                baldes[rotulo] += 1
                break
    return {"labels": list(baldes.keys()), "valores": list(baldes.values())}


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
            contexto["graf_situacao"] = _grafico_ordenado(
                participantes, "situacao", Participante.Situacao.choices
            )
            contexto["graf_uf"] = _grafico_top(participantes, "uf", limite=10)
            contexto["graf_cidade"] = _grafico_top(participantes, "cidade", limite=5)
            contexto["graf_genero"] = _grafico_top(
                participantes, "genero", limite=6, choices=Participante.Genero.choices
            )
            contexto["graf_renda"] = _grafico_ordenado(
                participantes, "faixa_renda", Participante.FaixaRenda.choices
            )
            contexto["graf_escolaridade"] = _grafico_ordenado(
                participantes, "escolaridade", Participante.Escolaridade.choices
            )

            contexto["graf_idade"] = _grafico_faixa_etaria(participantes)

    if request.user.tem_permissao("projetos.ver"):
        contexto["total_projetos"] = Projeto.objects.exclude(status=Projeto.Status.CONCLUIDO).count()

    if request.user.tem_permissao("participacoes.ver"):
        participacoes = Participacao.objects.all()
        contexto["total_participacoes"] = participacoes.count()
        contexto["graf_pipeline"] = _grafico_ordenado(participacoes, "etapa", Participacao.Etapa.choices)

    return render(request, "core/home.html", contexto)


@login_required
@requer_permissao("participantes.ver")
def dashboard_segmento(request):
    segmento_valores = {valor for valor, _ in Projeto.Segmento.choices}
    segmento_atual = request.GET.get("segmento")
    if segmento_atual not in segmento_valores:
        segmento_atual = None

    comparativo_labels = []
    comparativo_valores = []
    for valor, label in Projeto.Segmento.choices:
        total = Participante.objects.filter(participacoes__projeto__segmento=valor).distinct().count()
        comparativo_labels.append(label)
        comparativo_valores.append(total)

    contexto = {
        "segmentos": Projeto.Segmento.choices,
        "segmento_atual": segmento_atual,
        "graf_comparativo": {"labels": comparativo_labels, "valores": comparativo_valores},
    }

    if segmento_atual:
        participantes = Participante.objects.filter(
            participacoes__projeto__segmento=segmento_atual
        ).distinct()
        total = participantes.count()
        contexto["total_no_segmento"] = total
        if total:
            contexto["graf_genero_seg"] = _grafico_top(
                participantes, "genero", limite=6, choices=Participante.Genero.choices
            )
            contexto["graf_renda_seg"] = _grafico_ordenado(
                participantes, "faixa_renda", Participante.FaixaRenda.choices
            )
            contexto["graf_idade_seg"] = _grafico_faixa_etaria(participantes)
            contexto["graf_cidade_seg"] = _grafico_top(participantes, "cidade", limite=5)

    return render(request, "core/dashboard_segmento.html", contexto)
