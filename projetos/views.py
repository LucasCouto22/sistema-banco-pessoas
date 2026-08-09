from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.permissions import requer_permissao
from pessoas.links import TOKEN_MAX_AGE, gerar_token_captacao

from .forms import ProjetoForm
from .models import Projeto


@login_required
@requer_permissao("projetos.ver")
def lista(request):
    projetos = Projeto.objects.all()
    return render(request, "projetos/lista.html", {"projetos": projetos})


@login_required
@requer_permissao("projetos.ver")
def detalhe(request, pk):
    projeto = get_object_or_404(Projeto, pk=pk)
    participacoes = projeto.participacoes.select_related("participante", "responsavel")
    return render(
        request,
        "projetos/detalhe.html",
        {
            "projeto": projeto,
            "participacoes": participacoes,
            "pode_editar": request.user.tem_permissao("projetos.gerenciar"),
            "pode_excluir": request.user.tem_permissao("projetos.excluir"),
        },
    )


@login_required
@requer_permissao("projetos.gerenciar")
def novo(request):
    if request.method == "POST":
        form = ProjetoForm(request.POST)
        if form.is_valid():
            projeto = form.save(commit=False)
            projeto.criado_por = request.user
            projeto.save()
            messages.success(request, f"Projeto {projeto.nome} criado.")
            return redirect("projetos:detalhe", pk=projeto.pk)
    else:
        form = ProjetoForm()
    return render(request, "projetos/form.html", {"form": form, "titulo": "Novo projeto"})


@login_required
@requer_permissao("projetos.gerenciar")
def editar(request, pk):
    projeto = get_object_or_404(Projeto, pk=pk)
    if request.method == "POST":
        form = ProjetoForm(request.POST, instance=projeto)
        if form.is_valid():
            form.save()
            messages.success(request, "Projeto atualizado.")
            return redirect("projetos:detalhe", pk=projeto.pk)
    else:
        form = ProjetoForm(instance=projeto)
    return render(request, "projetos/form.html", {"form": form, "titulo": f"Editar {projeto.nome}"})


@login_required
@requer_permissao("projetos.excluir")
def excluir(request, pk):
    projeto = get_object_or_404(Projeto, pk=pk)
    if request.method == "POST":
        nome = projeto.nome
        projeto.delete()
        messages.success(request, f"Projeto {nome} excluído.")
        return redirect("projetos:lista")
    return render(request, "projetos/excluir.html", {"projeto": projeto})


@login_required
@requer_permissao("projetos.gerenciar")
def gerar_link(request, pk):
    projeto = get_object_or_404(Projeto, pk=pk)
    token = gerar_token_captacao(projeto.id, request.user.id)
    link = request.build_absolute_uri(reverse("pessoas:cadastro_publico", args=[token]))
    return render(
        request,
        "projetos/link.html",
        {"projeto": projeto, "link": link, "horas_validade": TOKEN_MAX_AGE // 3600},
    )
