"""Formulário de resposta dinâmico: monta um `forms.Form` em tempo real a
partir das variáveis de um `Formulario` (uma por `FormularioVariavel`,
respeitando a ordem). `form.cleaned_data` já sai pronto pra gravar direto em
`RespostaFormulario.respostas_variaveis` — o `DjangoJSONEncoder` do campo
cuida de serializar Decimal/date; só o caminho inverso (JSON gravado → valor
"vivo" pra pré-popular o formulário na edição) precisa de conversão manual,
feita em `_valor_inicial`.

Tipo de resposta sem um widget específico (algum código cadastrado em
`TipoResposta` sem suporte de renderização ainda) cai em texto livre — decisão
explícita: mais importante deixar responder algo do que travar o formulário
inteiro por causa de um tipo exótico que ninguém terminou de implementar."""

from datetime import date
from decimal import Decimal, InvalidOperation

from django import forms

from .widgets import DropdownCheckboxSelectMultiple


def _campo_para_variavel(variavel):
    tipo = variavel.tipo_resposta.codigo
    obrigatoria = variavel.obrigatoria
    label = variavel.nome

    if tipo == "inteiro":
        return forms.IntegerField(required=obrigatoria, label=label)
    if tipo == "decimal":
        return forms.DecimalField(required=obrigatoria, label=label)
    if tipo == "data":
        # `format="%Y-%m-%d"` é obrigatório aqui: sem ele, o widget formata o
        # valor inicial no formato localizado (pt-br → dd/mm/aaaa), que um
        # <input type="date"> não reconhece — o navegador simplesmente
        # ignora e mostra o campo vazio, mesmo com a resposta já salva.
        return forms.DateField(
            required=obrigatoria,
            label=label,
            widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        )
    if tipo == "booleano":
        return forms.TypedChoiceField(
            required=obrigatoria,
            label=label,
            choices=[("sim", "Sim"), ("nao", "Não")],
            coerce=lambda v: v == "sim",
            empty_value=None,
            widget=forms.RadioSelect,
        )
    if tipo in ("select", "radio", "multipla_escolha"):
        opcoes = [(o.valor, o.valor) for o in variavel.opcoes.all()]
        if tipo == "select":
            return forms.ChoiceField(
                required=obrigatoria, label=label, choices=[("", "Selecione…"), *opcoes]
            )
        if tipo == "radio":
            return forms.ChoiceField(required=obrigatoria, label=label, choices=opcoes, widget=forms.RadioSelect)
        return forms.MultipleChoiceField(
            required=obrigatoria, label=label, choices=opcoes, widget=DropdownCheckboxSelectMultiple
        )
    if tipo == "texto_curto":
        return forms.CharField(required=obrigatoria, label=label, widget=forms.TextInput)
    # "texto" (resposta longa) e qualquer tipo sem suporte específico.
    return forms.CharField(required=obrigatoria, label=label, widget=forms.Textarea(attrs={"rows": 2}))


def _valor_inicial(tipo_codigo, valor_json):
    if valor_json is None:
        return None
    if tipo_codigo == "decimal":
        try:
            return Decimal(str(valor_json))
        except InvalidOperation:
            return None
    if tipo_codigo == "data":
        if isinstance(valor_json, date):
            return valor_json
        try:
            return date.fromisoformat(valor_json)
        except (TypeError, ValueError):
            return None
    if tipo_codigo == "booleano":
        if valor_json is True:
            return "sim"
        if valor_json is False:
            return "nao"
        return None
    return valor_json


def construir_form_resposta(formulario, dados_iniciais=None, data=None, somente_leitura=False):
    """Devolve (form, itens) — `form` é a instância do formulário dinâmico
    (uma pergunta por variável do `formulario`, na ordem cadastrada) e
    `itens` é a lista de `FormularioVariavel` na mesma ordem, útil pro
    template combinar rótulo/tipo com o campo (`{% for fv, campo in ... %}`).

    `somente_leitura=True` desabilita os campos — usado na prévia do
    formulário (`formulario_visualizar`), que reaproveita esse mesmo
    renderizador só pra mostrar como as perguntas aparecem, sem intenção de
    ninguém preencher ali."""
    itens = list(
        formulario.formulario_variaveis.select_related("variavel__tipo_resposta")
        .prefetch_related("variavel__opcoes")
        .order_by("ordem")
    )
    campos = {}
    for fv in itens:
        campo = _campo_para_variavel(fv.variavel)
        if somente_leitura:
            campo.disabled = True
            campo.required = False
        campos[fv.variavel.chave] = campo
    FormularioResposta = type("FormularioRespostaDinamico", (forms.Form,), campos)

    initial = {}
    if dados_iniciais:
        for fv in itens:
            chave = fv.variavel.chave
            if chave in dados_iniciais:
                initial[chave] = _valor_inicial(fv.variavel.tipo_resposta.codigo, dados_iniciais[chave])

    form = FormularioResposta(data, initial=initial)
    linhas = [(fv, form[fv.variavel.chave]) for fv in itens]
    return form, linhas
