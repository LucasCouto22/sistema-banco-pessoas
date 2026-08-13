import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from accounts.permissions import requer_permissao
from pessoas.forms import UploadCSVForm
from pessoas.links import gerar_token_captacao

from .forms import PerfilForm, ProjetoForm
from .models import Perfil, Projeto
from .perfil_lote import associar_cpfs, ler_cpfs


@login_required
@requer_permissao("projetos.ver")
def lista(request):
    projetos = Projeto.objects.all()
    return render(request, "projetos/lista.html", {"projetos": projetos})


@login_required
@requer_permissao("projetos.ver")
def detalhe(request, pk):
    projeto = get_object_or_404(Projeto, pk=pk)
    perfis = projeto.perfis.select_related("formulario")
    return render(
        request,
        "projetos/detalhe.html",
        {
            "projeto": projeto,
            "perfis": perfis,
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


# =========================================================================
# Perfis — de 1 a N por projeto, cada um com seu formulário e seus
# participantes. Geridos a partir da tela de detalhe do projeto (já salvo),
# não embutidos no formulário de criação — mesmo padrão de Formulário e
# Variável, que também são CRUDs à parte.
# =========================================================================


@login_required
@requer_permissao("projetos.gerenciar")
def perfil_novo(request, projeto_pk):
    projeto = get_object_or_404(Projeto, pk=projeto_pk)
    if request.method == "POST":
        form = PerfilForm(request.POST)
        if form.is_valid():
            perfil = form.save(commit=False)
            perfil.projeto = projeto
            perfil.save()
            messages.success(request, f'Perfil "{perfil.nome}" criado.')
            return redirect("projetos:detalhe", pk=projeto.pk)
    else:
        form = PerfilForm()
    return render(
        request, "projetos/perfil_form.html", {"form": form, "projeto": projeto, "titulo": "Novo perfil"}
    )


@login_required
@requer_permissao("projetos.gerenciar")
def perfil_editar(request, pk):
    perfil = get_object_or_404(Perfil.objects.select_related("projeto"), pk=pk)
    if request.method == "POST":
        form = PerfilForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil atualizado.")
            return redirect("projetos:detalhe", pk=perfil.projeto_id)
    else:
        form = PerfilForm(instance=perfil)
    return render(
        request,
        "projetos/perfil_form.html",
        {"form": form, "projeto": perfil.projeto, "titulo": f"Editar {perfil.nome}"},
    )


@login_required
@requer_permissao("projetos.gerenciar")
def perfil_excluir(request, pk):
    perfil = get_object_or_404(Perfil.objects.select_related("projeto"), pk=pk)
    if request.method == "POST":
        projeto_pk = perfil.projeto_id
        nome = perfil.nome
        perfil.delete()
        messages.success(request, f'Perfil "{nome}" excluído.')
        return redirect("projetos:detalhe", pk=projeto_pk)
    return render(request, "projetos/perfil_excluir.html", {"perfil": perfil})


@login_required
@requer_permissao("projetos.ver")
def perfil_detalhe(request, pk):
    perfil = get_object_or_404(Perfil.objects.select_related("projeto", "formulario"), pk=pk)
    participacoes = perfil.participacoes.select_related("participante", "responsavel")
    return render(
        request,
        "projetos/perfil_detalhe.html",
        {
            "perfil": perfil,
            "participacoes": participacoes,
            "pode_editar": request.user.tem_permissao("projetos.gerenciar"),
            "pode_associar": request.user.tem_permissao("participacoes.mover_etapa"),
        },
    )


@login_required
@requer_permissao("projetos.gerenciar")
def perfil_link(request, pk):
    perfil = get_object_or_404(Perfil.objects.select_related("projeto"), pk=pk)
    token = gerar_token_captacao(perfil.id, request.user.id)
    link = request.build_absolute_uri(reverse("pessoas:cadastro_publico", args=[token]))
    return render(request, "projetos/perfil_link.html", {"perfil": perfil, "link": link})


@login_required
@requer_permissao("participacoes.mover_etapa")
def perfil_associar_lote(request, pk):
    perfil = get_object_or_404(Perfil.objects.select_related("projeto"), pk=pk)
    resultado = None
    if request.method == "POST":
        form = UploadCSVForm(request.POST, request.FILES)
        if form.is_valid():
            cpfs = ler_cpfs(form.cleaned_data["arquivo"])
            if not cpfs:
                messages.error(request, "Não encontramos nenhum CPF nesse arquivo.")
            else:
                resultado = associar_cpfs(perfil, cpfs, request.user)
    else:
        form = UploadCSVForm()
    return render(
        request,
        "projetos/perfil_associar_lote.html",
        {"perfil": perfil, "form": form, "resultado": resultado},
    )


@login_required
@requer_permissao("participacoes.mover_etapa")
def perfil_associar_lote_modelo(request, pk):
    wb = Workbook()
    ws = wb.active
    ws.title = "Associação em lote"
    ws.append(["CPF"])
    celula = ws.cell(row=1, column=1)
    celula.font = Font(bold=True, color="FFFFFF")
    celula.fill = PatternFill("solid", fgColor="C4143F")
    ws.append(["111.444.777-35"])
    ws.column_dimensions["A"].width = 20

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    response = HttpResponse(
        buffer.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="modelo_associacao_lote.xlsx"'
    return response
