from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from accounts.permissions import requer_permissao
from participacoes.models import Participacao

from .forms import FormularioForm, VariavelForm, VariavelOpcaoFormSet, montar_formset_variaveis
from .models import Formulario, FormularioVariavel, RespostaFormulario, TipoResposta, Variavel
from .respostas import construir_form_resposta


@login_required
@requer_permissao("variaveis.ver")
def variaveis_lista(request):
    variaveis = Variavel.objects.select_related("tipo_resposta").all()
    return render(request, "formularios/variaveis_lista.html", {"variaveis": variaveis})


def _contexto_tipos_resposta():
    tipos = TipoResposta.objects.all()
    return {
        "tipos_resposta": tipos,
        "tipos_resposta_por_id": {str(t.pk): t.codigo for t in tipos},
    }


def _salvar_variavel_com_opcoes(request, form, formset):
    """Valida forma + opções juntas (só é obrigatório ter opção se o tipo de
    resposta exigir) e salva tudo numa transação — evita gravar a variável e
    descobrir depois que as opções eram inválidas."""
    if not (form.is_valid() and formset.is_valid()):
        return False

    tipo = form.cleaned_data["tipo_resposta"]
    opcoes_preenchidas = [
        f for f in formset.forms if f.cleaned_data.get("valor") and not f.cleaned_data.get("DELETE")
    ]
    if tipo.usa_opcoes and not opcoes_preenchidas:
        messages.error(request, "Adicione pelo menos uma opção pra este tipo de resposta.")
        return False

    with transaction.atomic():
        variavel = form.save(commit=False)
        if not variavel.criado_por_id:
            variavel.criado_por = request.user
        variavel.save()

        opcoes = formset.save(commit=False)
        for indice, opcao in enumerate(opcoes):
            opcao.variavel = variavel
            opcao.ordem = indice
            opcao.save()
        for excluida in formset.deleted_objects:
            excluida.delete()

    return variavel


@login_required
@requer_permissao("variaveis.gerenciar")
def variavel_novo(request):
    if request.method == "POST":
        form = VariavelForm(request.POST)
        formset = VariavelOpcaoFormSet(request.POST, instance=Variavel())
        variavel = _salvar_variavel_com_opcoes(request, form, formset)
        if variavel:
            messages.success(request, f'Variável "{variavel.nome}" criada.')
            return redirect("formularios:variaveis_lista")
    else:
        form = VariavelForm()
        formset = VariavelOpcaoFormSet(instance=Variavel())
    return render(
        request,
        "formularios/variavel_form.html",
        {"form": form, "formset": formset, "titulo": "Nova variável", **_contexto_tipos_resposta()},
    )


@login_required
@requer_permissao("variaveis.gerenciar")
def variavel_editar(request, pk):
    variavel = get_object_or_404(Variavel, pk=pk)
    if request.method == "POST":
        form = VariavelForm(request.POST, instance=variavel)
        formset = VariavelOpcaoFormSet(request.POST, instance=variavel)
        if _salvar_variavel_com_opcoes(request, form, formset):
            messages.success(request, f'Variável "{variavel.nome}" atualizada.')
            return redirect("formularios:variaveis_lista")
    else:
        form = VariavelForm(instance=variavel)
        formset = VariavelOpcaoFormSet(instance=variavel)
    return render(
        request,
        "formularios/variavel_form.html",
        {"form": form, "formset": formset, "titulo": f"Editar {variavel.nome}", **_contexto_tipos_resposta()},
    )


@login_required
@requer_permissao("variaveis.excluir")
def variavel_excluir(request, pk):
    variavel = get_object_or_404(Variavel, pk=pk)
    if request.method == "POST":
        nome = variavel.nome
        try:
            variavel.delete()
        except ProtectedError:
            messages.error(
                request,
                f'A variável "{nome}" já está em uso em pelo menos um formulário e não pode ser excluída — '
                "desative-a em vez de excluir.",
            )
            return redirect("formularios:variaveis_lista")
        messages.success(request, f'Variável "{nome}" excluída.')
        return redirect("formularios:variaveis_lista")
    return render(request, "formularios/variavel_excluir.html", {"variavel": variavel})


@login_required
@requer_permissao("formularios.ver")
def formularios_lista(request):
    formularios = Formulario.objects.all().prefetch_related("variaveis")
    return render(request, "formularios/formularios_lista.html", {"formularios": formularios})


@login_required
@requer_permissao("formularios.ver")
def formulario_visualizar(request, pk):
    formulario = get_object_or_404(Formulario, pk=pk)
    form, linhas = construir_form_resposta(formulario, somente_leitura=True)
    return render(
        request,
        "formularios/formulario_visualizar.html",
        {"formulario": formulario, "form": form, "linhas": linhas},
    )


def _salvar_formulario_com_variaveis(request, form, formset):
    if not (form.is_valid() and formset.is_valid()):
        return False

    with transaction.atomic():
        formulario = form.save(commit=False)
        if not formulario.criado_por_id:
            formulario.criado_por = request.user
        formulario.save()

        incluidas = {}
        for subform in formset.forms:
            if not subform.cleaned_data.get("incluir"):
                continue
            incluidas[subform.cleaned_data["variavel_id"]] = subform.cleaned_data.get("ordem") or 0

        FormularioVariavel.objects.filter(formulario=formulario).exclude(
            variavel_id__in=incluidas.keys()
        ).delete()
        for variavel_id, ordem in incluidas.items():
            FormularioVariavel.objects.update_or_create(
                formulario=formulario, variavel_id=variavel_id, defaults={"ordem": ordem}
            )

    return formulario


@login_required
@requer_permissao("formularios.gerenciar")
def formulario_novo(request):
    if request.method == "POST":
        form = FormularioForm(request.POST)
        linhas, formset = montar_formset_variaveis(data=request.POST)
        formulario = _salvar_formulario_com_variaveis(request, form, formset)
        if formulario:
            messages.success(request, f'Formulário "{formulario.nome}" criado.')
            return redirect("formularios:formularios_lista")
    else:
        form = FormularioForm()
        linhas, formset = montar_formset_variaveis()
    return render(
        request,
        "formularios/formulario_form.html",
        {"form": form, "formset": formset, "linhas": linhas, "titulo": "Novo formulário"},
    )


@login_required
@requer_permissao("formularios.gerenciar")
def formulario_editar(request, pk):
    formulario = get_object_or_404(Formulario, pk=pk)
    if request.method == "POST":
        form = FormularioForm(request.POST, instance=formulario)
        linhas, formset = montar_formset_variaveis(formulario=formulario, data=request.POST)
        if _salvar_formulario_com_variaveis(request, form, formset):
            messages.success(request, f'Formulário "{formulario.nome}" atualizado.')
            return redirect("formularios:formularios_lista")
    else:
        form = FormularioForm(instance=formulario)
        linhas, formset = montar_formset_variaveis(formulario=formulario)
    return render(
        request,
        "formularios/formulario_form.html",
        {"form": form, "formset": formset, "linhas": linhas, "titulo": f"Editar {formulario.nome}"},
    )


@login_required
@requer_permissao("formularios.excluir")
def formulario_excluir(request, pk):
    formulario = get_object_or_404(Formulario, pk=pk)
    if request.method == "POST":
        nome = formulario.nome
        try:
            formulario.delete()
        except ProtectedError:
            messages.error(
                request,
                f'O formulário "{nome}" já está em uso em pelo menos um perfil e não pode ser excluído — '
                "desative-o em vez de excluir.",
            )
            return redirect("formularios:formularios_lista")
        messages.success(request, f'Formulário "{nome}" excluído.')
        return redirect("formularios:formularios_lista")
    return render(request, "formularios/formulario_excluir.html", {"formulario": formulario})


@login_required
@requer_permissao("respostas.preencher")
def responder_formulario(request, participacao_id, formulario_id):
    participacao = get_object_or_404(Participacao, pk=participacao_id)
    formulario = get_object_or_404(Formulario, pk=formulario_id)
    # O formulário só pode ser respondido aqui se realmente estiver
    # associado ao perfil dessa participação — sem essa checagem, dá pra
    # montar a URL na mão e responder um formulário de outro perfil qualquer.
    if not participacao.perfil.formularios.filter(pk=formulario.pk).exists():
        messages.error(request, f'"{formulario.nome}" não está associado ao perfil desta participação.')
        return redirect("participacoes:detalhe", pk=participacao.pk)

    resposta_existente = RespostaFormulario.objects.filter(
        participacao=participacao, formulario=formulario
    ).first()

    if request.method == "POST":
        form, linhas = construir_form_resposta(formulario, data=request.POST)
        if form.is_valid():
            RespostaFormulario.objects.update_or_create(
                participacao=participacao,
                formulario=formulario,
                defaults={"respostas_variaveis": form.cleaned_data},
            )
            messages.success(request, f'Respostas de "{formulario.nome}" salvas.')
            return redirect("participacoes:detalhe", pk=participacao.pk)
    else:
        dados_iniciais = resposta_existente.respostas_variaveis if resposta_existente else None
        form, linhas = construir_form_resposta(formulario, dados_iniciais=dados_iniciais)

    return render(
        request,
        "formularios/responder_formulario.html",
        {"participacao": participacao, "formulario": formulario, "form": form, "linhas": linhas},
    )
