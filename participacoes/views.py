from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.permissions import requer_permissao
from formularios.models import RespostaFormulario
from projetos.models import Projeto

from . import exportacao
from .forms import AvaliacaoForm, ParticipacaoForm
from .models import Avaliacao, Participacao

ITENS_POR_PAGINA = 10


def _participacoes_filtradas(request):
    """Aplica os filtros de `?nome=&projeto=&etapa=&status=&nota=` — usado tanto
    pela tela de lista quanto pela exportação em PDF/XLSX, pra exportar sempre
    exatamente o que está sendo visto na tela."""
    participacoes = Participacao.objects.select_related(
        "participante", "perfil__projeto", "responsavel", "avaliacao", "avaliacao__avaliado_por"
    ).annotate(
        nota_media=(F("avaliacao__comunicacao") + F("avaliacao__pontualidade") + F("avaliacao__repertorio")) / 3.0
    )
    nome = request.GET.get("nome", "").strip()
    projeto_id = request.GET.get("projeto")
    etapa = request.GET.get("etapa")
    status = request.GET.get("status")
    nota = request.GET.get("nota", "").strip()

    if nome:
        participacoes = participacoes.filter(participante__nome__icontains=nome)
    if projeto_id:
        participacoes = participacoes.filter(perfil__projeto_id=projeto_id)
    if etapa:
        participacoes = participacoes.filter(etapa=etapa)
    if status:
        participacoes = participacoes.filter(status=status)
    if nota == "sem_avaliacao":
        participacoes = participacoes.filter(avaliacao__isnull=True)
    elif nota:
        try:
            participacoes = participacoes.filter(nota_media__gte=float(nota))
        except ValueError:
            pass

    filtros = {
        "nome": nome,
        "projeto": projeto_id or "",
        "etapa": etapa or "",
        "status": status or "",
        "nota": nota,
    }
    return participacoes, filtros


@login_required
@requer_permissao("participacoes.ver")
def lista(request):
    participacoes, filtros = _participacoes_filtradas(request)
    paginator = Paginator(participacoes, ITENS_POR_PAGINA)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "participacoes/lista.html",
        {
            "participacoes": page_obj,
            "page_obj": page_obj,
            "projetos": Projeto.objects.all().order_by("nome"),
            "etapas": Participacao.Etapa.choices,
            "status_list": Participacao.Status.choices,
            "filtro_nome": filtros["nome"],
            "filtro_projeto": filtros["projeto"],
            "filtro_etapa": filtros["etapa"],
            "filtro_nota": filtros["nota"],
        },
    )


@login_required
@requer_permissao("participacoes.ver")
def exportar(request, formato):
    participacoes, filtros = _participacoes_filtradas(request)
    pode_revelar_pii = request.user.tem_permissao("participantes.revelar_pii")
    if formato == "xlsx":
        return exportacao.gerar_xlsx(participacoes, pode_revelar_pii)
    if formato == "pdf":
        return exportacao.gerar_pdf(participacoes, pode_revelar_pii, filtros)
    raise Http404


@login_required
@requer_permissao("participacoes.ver")
def kanban(request):
    colunas = []
    for etapa_valor, etapa_label in Participacao.Etapa.choices:
        itens = Participacao.objects.filter(etapa=etapa_valor).select_related("participante", "perfil__projeto")
        colunas.append({"valor": etapa_valor, "label": etapa_label, "itens": itens})
    return render(request, "participacoes/kanban.html", {"colunas": colunas})


@login_required
@requer_permissao("participacoes.ver")
def detalhe(request, pk):
    participacao = get_object_or_404(
        Participacao.objects.select_related("participante", "perfil__projeto", "responsavel"), pk=pk
    )
    formularios_do_projeto = []
    if request.user.tem_permissao("respostas.ver") and participacao.perfil.formulario_id:
        resposta = RespostaFormulario.objects.filter(
            participacao=participacao, formulario_id=participacao.perfil.formulario_id
        ).first()
        formularios_do_projeto.append({"formulario": participacao.perfil.formulario, "resposta": resposta})
    avaliacao = getattr(participacao, "avaliacao", None)
    pode_avaliar = request.user.tem_permissao("avaliacao.criar")
    return render(
        request,
        "participacoes/detalhe.html",
        {
            "participacao": participacao,
            "avaliacao": avaliacao,
            "avaliacao_form": AvaliacaoForm(instance=avaliacao) if pode_avaliar else None,
            "formularios_do_projeto": formularios_do_projeto,
            "pode_avaliar": pode_avaliar,
            "pode_preencher_respostas": request.user.tem_permissao("respostas.preencher"),
        },
    )


@login_required
@requer_permissao("participacoes.mover_etapa")
def nova(request):
    if request.method == "POST":
        form = ParticipacaoForm(request.POST)
        if form.is_valid():
            participacao = form.save(commit=False)
            participacao.responsavel = request.user
            participacao.save()
            messages.success(request, "Participante associado ao perfil.")
            return redirect("participacoes:kanban")
    else:
        # `?perfil=<id>` vem do botão "Associar pessoa" na tela do perfil,
        # pra já chegar com o perfil certo pré-selecionado.
        form = ParticipacaoForm(initial={"perfil": request.GET.get("perfil")})
    return render(request, "participacoes/form.html", {"form": form, "titulo": "Associar a perfil"})


@login_required
@requer_permissao("participacoes.mover_etapa")
@require_POST
def avancar(request, pk):
    participacao = get_object_or_404(Participacao, pk=pk)
    if participacao.avancar_etapa():
        messages.success(request, f"{participacao.participante.nome} avançou para {participacao.get_etapa_display()}.")
    else:
        messages.info(request, "Esta participação já está na última etapa do funil.")
    destino = request.POST.get("proximo") or "participacoes:kanban"
    return redirect(destino)


@login_required
@requer_permissao("avaliacao.criar")
@require_POST
def avaliar(request, pk):
    # Sem tela própria — o preenchimento acontece num modal (na lista ou no
    # detalhe da participação), então aqui só existe o POST. Sucesso ou
    # erro, volta sempre pro detalhe: lá o formulário já vem pré-preenchido
    # com os valores certos (inclusive os que falharam, pra corrigir).
    participacao = get_object_or_404(Participacao, pk=pk)
    instancia = Avaliacao.objects.filter(participacao=participacao).first()
    form = AvaliacaoForm(request.POST, instance=instancia)
    if form.is_valid():
        avaliacao = form.save(commit=False)
        avaliacao.participacao = participacao
        avaliacao.avaliado_por = request.user
        avaliacao.save()
        messages.success(request, "Avaliação registrada.")
    else:
        messages.error(request, "Não foi possível salvar — escolha uma nota de 1 a 5 para cada critério.")
    return redirect("participacoes:detalhe", pk=participacao.pk)
