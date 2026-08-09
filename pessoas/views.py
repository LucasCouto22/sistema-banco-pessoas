import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Value
from django.db.models.functions import Replace
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

CAMPOS_PII_REVELAVEIS = ("cpf", "telefone", "email")

from accounts.models import Usuario
from accounts.permissions import requer_permissao
from auditoria.models import RegistroAcesso, registrar
from participacoes.models import Participacao
from projetos.models import Projeto
from termos.models import Termo

from .forms import (
    CadastroPublicoForm,
    EscolherProjetoWizardForm,
    ParticipanteForm,
    ParticipanteWizardForm,
    UploadCSVForm,
    participante_wizard_formset,
)
from .links import ler_token_captacao
from .models import Participante
from .validators import normalizar_cpf
from .wizard_csv import CABECALHO_MODELO, LINHA_EXEMPLO, ler_csv

WIZ_SESSION_KEY = "wizard_importacao"


def _versao_lgpd_vigente():
    # order_by explícito: se alguém cadastrar mais de um documento do tipo
    # "Consentimento" por engano, sempre usamos o mais antigo (o original),
    # em vez de depender da ordem não garantida do banco.
    termo = Termo.objects.filter(tipo=Termo.Tipo.CONSENTIMENTO).order_by("id").first()
    return termo.versao_vigente if termo else None


def _cpf_ja_cadastrado(cpf_normalizado):
    if not cpf_normalizado:
        return False
    return (
        Participante.objects.annotate(
            cpf_normalizado=Replace(Replace("cpf", Value("."), Value("")), Value("-"), Value(""))
        )
        .filter(cpf_normalizado=cpf_normalizado)
        .exists()
    )


@login_required
@requer_permissao("participantes.ver")
@ensure_csrf_cookie
def lista(request):
    q = request.GET.get("q", "").strip()
    participantes = Participante.objects.all()
    if q:
        participantes = participantes.filter(
            Q(nome__icontains=q) | Q(cpf__icontains=q) | Q(codigo__icontains=q)
        )
    pode_revelar = request.user.tem_permissao("participantes.revelar_pii")
    return render(
        request,
        "pessoas/lista.html",
        {"participantes": participantes, "q": q, "pode_revelar": pode_revelar},
    )


@login_required
@requer_permissao("participantes.ver")
@ensure_csrf_cookie
def detalhe(request, pk):
    participante = get_object_or_404(Participante, pk=pk)
    pode_revelar = request.user.tem_permissao("participantes.revelar_pii")
    pode_pagamento = request.user.tem_permissao("pagamento.ver")
    pode_editar = request.user.tem_permissao("participantes.gerenciar")
    pode_excluir = request.user.tem_permissao("participantes.excluir")
    return render(
        request,
        "pessoas/detalhe.html",
        {
            "participante": participante,
            "pode_revelar": pode_revelar,
            "pode_pagamento": pode_pagamento,
            "pode_editar": pode_editar,
            "pode_excluir": pode_excluir,
        },
    )


@login_required
@requer_permissao("participantes.revelar_pii")
@require_POST
def revelar_campo(request, pk, campo):
    if campo not in CAMPOS_PII_REVELAVEIS:
        raise Http404
    participante = get_object_or_404(Participante, pk=pk)
    valor = getattr(participante, campo)
    registrar(
        request.user,
        participante.codigo,
        RegistroAcesso.Acao.VISUALIZACAO,
        f"Campo '{campo}' revelado sem máscara",
    )
    return JsonResponse({"valor": valor})


@login_required
@requer_permissao("participantes.excluir")
def excluir(request, pk):
    participante = get_object_or_404(Participante, pk=pk)
    if request.method == "POST":
        nome = participante.nome
        codigo = participante.codigo
        participante.delete()
        registrar(request.user, codigo, RegistroAcesso.Acao.ALTERACAO, f"Participante {nome} excluído")
        messages.success(request, f"{nome} foi excluído(a) do Banco de Pessoas.")
        return redirect("pessoas:lista")
    return render(
        request,
        "pessoas/excluir.html",
        {"participante": participante, "total_participacoes": participante.participacoes.count()},
    )


@login_required
@requer_permissao("participantes.gerenciar")
def novo(request):
    pode_pagamento = request.user.tem_permissao("pagamento.ver")
    if request.method == "POST":
        form = ParticipanteForm(request.POST, pode_ver_pagamento=pode_pagamento)
        if form.is_valid():
            participante = form.save(commit=False)
            participante.criado_por = request.user
            if participante.consentimento_lgpd:
                participante.consentimento_versao = _versao_lgpd_vigente()
            participante.save()
            messages.success(request, f"Participante {participante.codigo} cadastrado com sucesso.")
            return redirect("pessoas:detalhe", pk=participante.pk)
    else:
        form = ParticipanteForm(pode_ver_pagamento=pode_pagamento)
    return render(request, "pessoas/form.html", {"form": form, "titulo": "Novo participante"})


@login_required
@requer_permissao("participantes.gerenciar")
def editar(request, pk):
    participante = get_object_or_404(Participante, pk=pk)
    pode_pagamento = request.user.tem_permissao("pagamento.ver")
    if request.method == "POST":
        form = ParticipanteForm(request.POST, instance=participante, pode_ver_pagamento=pode_pagamento)
        if form.is_valid():
            participante = form.save(commit=False)
            if participante.consentimento_lgpd and not participante.consentimento_versao_id:
                participante.consentimento_versao = _versao_lgpd_vigente()
            participante.save()
            messages.success(request, "Dados do participante atualizados.")
            return redirect("pessoas:detalhe", pk=participante.pk)
    else:
        form = ParticipanteForm(instance=participante, pode_ver_pagamento=pode_pagamento)
    return render(
        request,
        "pessoas/form.html",
        {"form": form, "titulo": f"Editar {participante.nome}"},
    )


# =========================================================================
# Wizard de cadastro em lote (novos participantes)
# =========================================================================

WIZ_STEPS = ["Banco de dados", "Novos participantes", "Dados", "Revisão"]


def _validar_linha_csv(dados):
    dados = dict(dados)
    dados.setdefault("situacao", Participante.Situacao.PENDENTE)
    form = ParticipanteWizardForm(data=dados)
    valido = form.is_valid()
    erros = None
    if not valido:
        erros = {campo: [str(e) for e in lista] for campo, lista in form.errors.items()}
    return {"dados": dados, "valido": valido, "erros": erros, "consentimento": False}


@login_required
@requer_permissao("participantes.gerenciar")
def wizard_projeto(request):
    request.session.pop(WIZ_SESSION_KEY, None)
    if request.method == "POST":
        form = EscolherProjetoWizardForm(request.POST)
        if form.is_valid():
            projeto = form.cleaned_data["projeto"]
            request.session[WIZ_SESSION_KEY] = {
                "projeto_id": projeto.id if projeto else None,
                "modo": None,
                "linhas": [],
            }
            return redirect("pessoas:wizard_modo")
    else:
        form = EscolherProjetoWizardForm()
    return render(
        request,
        "pessoas/wizard_projeto.html",
        {"form": form, "steps": WIZ_STEPS, "step_atual": 0},
    )


@login_required
@requer_permissao("participantes.gerenciar")
def wizard_modo(request):
    estado = request.session.get(WIZ_SESSION_KEY)
    if estado is None:
        messages.info(request, "Comece escolhendo o destino dos novos participantes.")
        return redirect("pessoas:wizard_projeto")
    if request.method == "POST":
        modo = request.POST.get("modo")
        if modo not in ("CSV", "MANUAL"):
            messages.error(request, "Escolha uma forma de cadastro para continuar.")
        else:
            estado["modo"] = modo
            request.session[WIZ_SESSION_KEY] = estado
            if modo == "CSV":
                return redirect("pessoas:wizard_dados_csv")
            return redirect("pessoas:wizard_dados_manual")
    return render(
        request,
        "pessoas/wizard_modo.html",
        {"steps": WIZ_STEPS, "step_atual": 1},
    )


@login_required
@requer_permissao("participantes.gerenciar")
def wizard_dados_csv(request):
    estado = request.session.get(WIZ_SESSION_KEY)
    if estado is None or estado.get("modo") != "CSV":
        return redirect("pessoas:wizard_projeto")

    if request.method == "POST":
        form = UploadCSVForm(request.POST, request.FILES)
        if form.is_valid():
            linhas_csv = ler_csv(form.cleaned_data["arquivo"])
            if not linhas_csv:
                messages.error(request, "Não encontramos nenhuma linha de dados nesse arquivo.")
            else:
                estado["linhas"] = [_validar_linha_csv(dados) for dados in linhas_csv]
                request.session[WIZ_SESSION_KEY] = estado
                return redirect("pessoas:wizard_revisao")
    else:
        form = UploadCSVForm()
    return render(
        request,
        "pessoas/wizard_dados_csv.html",
        {"form": form, "steps": WIZ_STEPS, "step_atual": 2},
    )


@login_required
@requer_permissao("participantes.gerenciar")
def wizard_modelo_csv(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="modelo_importacao_participantes.csv"'
    writer = csv.writer(response)
    writer.writerow(CABECALHO_MODELO)
    writer.writerow(LINHA_EXEMPLO)
    return response


@login_required
@requer_permissao("participantes.gerenciar")
def wizard_dados_manual(request):
    estado = request.session.get(WIZ_SESSION_KEY)
    if estado is None or estado.get("modo") != "MANUAL":
        return redirect("pessoas:wizard_projeto")

    try:
        quantidade = max(1, min(20, int(request.GET.get("linhas", 5))))
    except ValueError:
        quantidade = 5

    if request.method == "POST":
        FormSet = participante_wizard_formset()
        formset = FormSet(request.POST)
        if formset.is_valid():
            linhas = []
            for f in formset:
                if not f.cleaned_data or not f.cleaned_data.get("nome"):
                    continue
                dados = dict(f.cleaned_data)
                if dados.get("data_nascimento"):
                    dados["data_nascimento"] = dados["data_nascimento"].isoformat()
                linhas.append({"dados": dados, "valido": True, "erros": None, "consentimento": False})
            if not linhas:
                messages.error(request, "Preencha ao menos um participante antes de continuar.")
            else:
                estado["linhas"] = linhas
                request.session[WIZ_SESSION_KEY] = estado
                return redirect("pessoas:wizard_revisao")
    else:
        FormSet = participante_wizard_formset(extra=quantidade)
        formset = FormSet()

    return render(
        request,
        "pessoas/wizard_dados_manual.html",
        {"formset": formset, "quantidade": quantidade, "steps": WIZ_STEPS, "step_atual": 2},
    )


@login_required
@requer_permissao("participantes.gerenciar")
def wizard_revisao(request):
    estado = request.session.get(WIZ_SESSION_KEY)
    if not estado or not estado.get("linhas"):
        messages.info(request, "Nenhum participante para revisar ainda.")
        return redirect("pessoas:wizard_projeto")

    linhas = estado["linhas"]
    projeto = None
    if estado.get("projeto_id"):
        projeto = Projeto.objects.filter(pk=estado["projeto_id"]).first()

    if request.method == "POST":
        vistos_no_lote = set()
        criados = 0
        pulados = 0
        versao_lgpd = _versao_lgpd_vigente()

        for indice, linha in enumerate(linhas):
            aceite = request.POST.get(f"consentimento_{indice}") == "on"
            dados = dict(linha["dados"])
            dados["situacao"] = dados.get("situacao") or Participante.Situacao.PENDENTE
            form = ParticipanteWizardForm(data=dados)
            valido = form.is_valid()
            cpf_normalizado = normalizar_cpf(dados.get("cpf", ""))
            duplicado_no_lote = bool(cpf_normalizado) and cpf_normalizado in vistos_no_lote
            ja_existe = _cpf_ja_cadastrado(cpf_normalizado)

            if not (valido and aceite) or duplicado_no_lote or ja_existe:
                pulados += 1
                continue

            vistos_no_lote.add(cpf_normalizado)
            participante = form.save(commit=False)
            participante.criado_por = request.user
            participante.consentimento_lgpd = True
            participante.consentimento_versao = versao_lgpd
            participante.save()
            criados += 1

            if projeto is not None:
                Participacao.objects.get_or_create(
                    participante=participante,
                    projeto=projeto,
                    defaults={"etapa": Participacao.Etapa.ANALISE_PERFIL, "responsavel": request.user},
                )

        del request.session[WIZ_SESSION_KEY]

        if criados:
            messages.success(request, f"{criados} participante(s) importado(s) com sucesso.")
        if pulados:
            messages.info(
                request,
                f"{pulados} linha(s) não foram importadas (dados inválidos, sem consentimento "
                "marcado ou CPF já cadastrado).",
            )
        if not criados and not pulados:
            messages.info(request, "Nenhuma linha foi processada.")
        return redirect("pessoas:lista")

    linhas_exibicao = [{"indice": indice, **linha} for indice, linha in enumerate(linhas)]
    return render(
        request,
        "pessoas/wizard_revisao.html",
        {
            "linhas": linhas_exibicao,
            "projeto": projeto,
            "steps": WIZ_STEPS,
            "step_atual": 3,
        },
    )


@login_required
@requer_permissao("participantes.gerenciar")
def wizard_cancelar(request):
    request.session.pop(WIZ_SESSION_KEY, None)
    messages.info(request, "Importação cancelada.")
    return redirect("pessoas:lista")


# =========================================================================
# Triagem (aprovar/descartar participantes pendentes)
# =========================================================================


@login_required
@requer_permissao("participantes.gerenciar")
@require_POST
def aprovar(request, pk):
    participante = get_object_or_404(Participante, pk=pk)
    participante.situacao = Participante.Situacao.APROVADO
    participante.save(update_fields=["situacao"])
    registrar(request.user, participante.codigo, RegistroAcesso.Acao.ALTERACAO, "Participante aprovado na triagem")
    messages.success(request, f"{participante.nome} aprovado(a).")
    return redirect("pessoas:detalhe", pk=pk)


@login_required
@requer_permissao("participantes.gerenciar")
@require_POST
def descartar(request, pk):
    participante = get_object_or_404(Participante, pk=pk)
    participante.situacao = Participante.Situacao.DESCARTADO
    participante.save(update_fields=["situacao"])
    Participacao.objects.filter(
        participante=participante, etapa=Participacao.Etapa.ANALISE_PERFIL
    ).delete()
    registrar(request.user, participante.codigo, RegistroAcesso.Acao.ALTERACAO, "Participante descartado na triagem")
    messages.info(request, f"{participante.nome} descartado(a).")
    return redirect("pessoas:detalhe", pk=pk)


# =========================================================================
# Página pública de cadastro (sem login) — acessada por link de recrutador
# =========================================================================


def cadastro_publico(request, token):
    try:
        payload = ler_token_captacao(token)
    except ValueError as exc:
        return render(request, "publico/link_invalido.html", {"mensagem": str(exc)}, status=410)

    projeto = Projeto.objects.filter(pk=payload["projeto_id"]).exclude(status=Projeto.Status.CONCLUIDO).first()
    if projeto is None:
        return render(
            request,
            "publico/link_invalido.html",
            {"mensagem": "Este projeto não está mais recebendo cadastros."},
            status=410,
        )

    recrutador = Usuario.objects.filter(pk=payload["recrutador_id"]).first()
    versao_lgpd = _versao_lgpd_vigente()

    if request.method == "POST":
        form = CadastroPublicoForm(request.POST)
        if form.is_valid():
            participante = form.save(commit=False)
            participante.situacao = Participante.Situacao.PENDENTE
            participante.origem_recrutador = recrutador
            participante.consentimento_versao = versao_lgpd
            participante.save()
            Participacao.objects.get_or_create(
                participante=participante,
                projeto=projeto,
                defaults={"etapa": Participacao.Etapa.ANALISE_PERFIL, "responsavel": recrutador},
            )
            return render(request, "publico/cadastro_ok.html", {"participante": participante, "projeto": projeto})
    else:
        form = CadastroPublicoForm()

    return render(
        request,
        "publico/cadastro.html",
        {"form": form, "projeto": projeto, "versao_lgpd": versao_lgpd},
    )
