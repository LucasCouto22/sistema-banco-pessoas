from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from accounts.permissions import requer_permissao

from .forms import TermoForm, VersaoTermoForm
from .models import LogAlteracao, Termo, VersaoTermo


@login_required
@requer_permissao("termos.ver")
def lista(request):
    termos = Termo.objects.prefetch_related("versoes")
    return render(request, "termos/lista.html", {"termos": termos})


@login_required
@requer_permissao("termos.ver")
def detalhe(request, pk):
    termo = get_object_or_404(Termo, pk=pk)
    versoes = termo.versoes.all()
    versao_id = request.GET.get("versao")
    if versao_id:
        versao_atual = get_object_or_404(VersaoTermo, pk=versao_id, termo=termo)
    else:
        versao_atual = termo.versao_vigente or versoes.first()
    logs = versao_atual.logs.all() if versao_atual else []
    return render(
        request,
        "termos/detalhe.html",
        {"termo": termo, "versoes": versoes, "versao_atual": versao_atual, "logs": logs},
    )


@login_required
@requer_permissao("termos.gerenciar")
def novo(request):
    if request.method == "POST":
        form = TermoForm(request.POST)
        if form.is_valid():
            termo = Termo.objects.create(nome=form.cleaned_data["nome"], tipo=form.cleaned_data["tipo"])
            versao_label = form.cleaned_data["versao"] or termo.proxima_versao()
            versao = VersaoTermo.objects.create(
                termo=termo,
                versao=versao_label,
                texto=form.cleaned_data["texto"],
                inicio_vigencia=form.cleaned_data["inicio_vigencia"],
                fim_vigencia=form.cleaned_data.get("fim_vigencia"),
                status=VersaoTermo.Status.VIGENTE,
                autor=request.user,
            )
            LogAlteracao.objects.create(
                versao=versao, usuario=request.user, acao=f"Documento criado com a versão {versao.versao}"
            )
            messages.success(request, f"Documento {termo.nome} criado ({versao.versao}).")
            return redirect("termos:detalhe", pk=termo.pk)
    else:
        form = TermoForm()
    return render(request, "termos/form.html", {"form": form, "titulo": "Novo termo ou contrato"})


@login_required
@requer_permissao("termos.gerenciar")
def nova_versao(request, pk):
    termo = get_object_or_404(Termo, pk=pk)
    if request.method == "POST":
        form = VersaoTermoForm(request.POST)
        if form.is_valid():
            vigente_atual = termo.versao_vigente
            nova = form.save(commit=False)
            nova.termo = termo
            nova.versao = termo.proxima_versao()
            nova.status = VersaoTermo.Status.VIGENTE
            nova.autor = request.user
            nova.save()
            if vigente_atual:
                vigente_atual.status = VersaoTermo.Status.SUBSTITUIDA
                vigente_atual.save(update_fields=["status"])
                LogAlteracao.objects.create(
                    versao=vigente_atual, usuario=request.user, acao=f"Substituída pela versão {nova.versao}"
                )
            LogAlteracao.objects.create(
                versao=nova, usuario=request.user, acao=f"Nova versão {nova.versao} publicada"
            )
            messages.success(request, f"Nova versão {nova.versao} publicada.")
            return redirect("termos:detalhe", pk=termo.pk)
    else:
        anterior = termo.versao_vigente
        form = VersaoTermoForm(initial={"texto": anterior.texto if anterior else ""})
    return render(request, "termos/versao_form.html", {"form": form, "termo": termo})
