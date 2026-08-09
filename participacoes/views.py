from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.permissions import requer_permissao

from .forms import AvaliacaoForm, ParticipacaoForm
from .models import Avaliacao, Participacao


@login_required
@requer_permissao("participacoes.ver")
def lista(request):
    participacoes = Participacao.objects.select_related("participante", "projeto", "responsavel")
    projeto_id = request.GET.get("projeto")
    etapa = request.GET.get("etapa")
    status = request.GET.get("status")
    if projeto_id:
        participacoes = participacoes.filter(projeto_id=projeto_id)
    if etapa:
        participacoes = participacoes.filter(etapa=etapa)
    if status:
        participacoes = participacoes.filter(status=status)
    return render(
        request,
        "participacoes/lista.html",
        {
            "participacoes": participacoes,
            "etapas": Participacao.Etapa.choices,
            "status_list": Participacao.Status.choices,
        },
    )


@login_required
@requer_permissao("participacoes.ver")
def kanban(request):
    colunas = []
    for etapa_valor, etapa_label in Participacao.Etapa.choices:
        itens = Participacao.objects.filter(etapa=etapa_valor).select_related("participante", "projeto")
        colunas.append({"valor": etapa_valor, "label": etapa_label, "itens": itens})
    return render(request, "participacoes/kanban.html", {"colunas": colunas})


@login_required
@requer_permissao("participacoes.mover_etapa")
def nova(request):
    if request.method == "POST":
        form = ParticipacaoForm(request.POST)
        if form.is_valid():
            participacao = form.save(commit=False)
            participacao.responsavel = request.user
            participacao.save()
            messages.success(request, "Participante associado ao projeto.")
            return redirect("participacoes:kanban")
    else:
        form = ParticipacaoForm()
    return render(request, "participacoes/form.html", {"form": form, "titulo": "Associar a projeto"})


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
def avaliar(request, pk):
    participacao = get_object_or_404(Participacao, pk=pk)
    instancia = Avaliacao.objects.filter(participacao=participacao).first()
    if request.method == "POST":
        form = AvaliacaoForm(request.POST, instance=instancia)
        if form.is_valid():
            avaliacao = form.save(commit=False)
            avaliacao.participacao = participacao
            avaliacao.avaliado_por = request.user
            avaliacao.save()
            messages.success(request, "Avaliação registrada.")
            return redirect("participacoes:lista")
    else:
        form = AvaliacaoForm(instance=instancia)
    return render(
        request,
        "participacoes/avaliar.html",
        {"form": form, "participacao": participacao},
    )
