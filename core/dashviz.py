"""Dados e componentes dos dashboards "Visão participantes" e "Visão por
segmento".

A parte interativa de ambos (mapa por estado, capitais, gênero, classe,
faixa etária, diagrama de Venn, seleção de segmento) roda inteiramente no
cliente — igual ao protótipo, que também nunca recalcula nada no servidor a
cada clique: os dados de cada participante são serializados uma vez aqui
(`dados_participantes_dashboard`, usada pelas duas telas) e todo
filtro/re-render acontece em `static/js/dashboard.js` e
`static/js/dashboard_segmento.js`. Um servidor que reconstrói HTML a cada
clique (como a versão antiga daqui fazia via querystring) é sempre mais
lento e mais tosco de usar do que isso.

A "Situação dos participantes" (na Visão participantes) é a única visão que
continua sendo montada no servidor: não existe no protótipo (não é um filtro
dele) e não precisa ser interativa, então não há motivo pra mandar mais
dados que o necessário pro cliente por causa dela."""

from django.utils import timezone

CAPITAIS_PRINCIPAIS = ["Rio de Janeiro", "São Paulo", "Brasília", "Fortaleza", "Salvador"]

COR_SITUACAO = {
    "PENDENTE": "var(--amber)",
    "APROVADO": "var(--green)",
    "DESCARTADO": "#C21807",
}

COR_ETAPA = {
    "ANALISE_PERFIL": "var(--blue)",
    "PREENCHIMENTO_DADOS": "var(--violet)",
    "CAPTACAO_MATERIAL": "var(--amber)",
    "ENTREVISTA": "var(--pink)",
    "PAGO": "var(--green)",
}

FAIXAS_ETARIAS = [
    ("18-24", 18, 24),
    ("25-34", 25, 34),
    ("35-44", 35, 44),
    ("45-54", 45, 54),
    ("55+", 55, 200),
]

def generos_disponiveis():
    """Rótulos de todas as opções de `Participante.Genero`, na ordem do
    cadastro — a lista de barras/legenda do gráfico "Gênero" dos dois
    dashboards. Antes disso era uma lista fixa de 4 rótulos no código
    (`Feminino/Masculino/Outro/Prefere não informar`) que sobrou de antes da
    realinhada de opções com o BP.xlsx (migração
    `pessoas/migrations/0008_campos_perfilamento_bp.py`, que trocou pra 7
    opções) — igual ao que tinha acontecido com "Classe social", ninguém
    tinha atualizado o dashboard nessa hora."""
    from pessoas.models import Participante

    return [rotulo for _codigo, rotulo in Participante.Genero.choices]


def faixas_renda_disponiveis():
    """(código, rótulo) de cada faixa de `Participante.FaixaRendaIndividual`,
    na ordem do cadastro (A→E) — a mesma pergunta "Renda individual" do
    formulário de participante. O gráfico "Classe social" dos dois
    dashboards usa essa lista pra montar as barras: quantas faixas o
    formulário tiver, é isso que aparece ali, sem juntar A/B nem D/E num
    bucket arbitrário como a versão anterior fazia."""
    from pessoas.models import Participante

    return list(Participante.FaixaRendaIndividual.choices)


def _idade_em(nascimento, hoje):
    anos = hoje.year - nascimento.year
    if (hoje.month, hoje.day) < (nascimento.month, nascimento.day):
        anos -= 1
    return anos


def _faixa_etaria(nascimento, hoje):
    idade = _idade_em(nascimento, hoje)
    for rotulo, minimo, maximo in FAIXAS_ETARIAS:
        if minimo <= idade <= maximo:
            return rotulo
    return None


def categorias_disponiveis():
    """Nomes de todas as `CategoriaFormulario` cadastradas, em ordem
    alfabética — a lista de abas/segmentos dos dois dashboards. Antes disso
    era uma lista fixa de 5 `Projeto.Segmento` no código; agora reflete o
    cadastro de verdade em "Configurações de Formulários / Categorias", e
    cresce/encolhe junto com ele sem precisar mexer em código."""
    from formularios.models import CategoriaFormulario

    return list(CategoriaFormulario.objects.order_by("nome").values_list("nome", flat=True))


def dados_participantes_dashboard(participantes):
    """Um registro compacto por participante — só os campos que o dashboard
    interativo usa pra filtrar e contar (`uf`, `gen`, `cls`, `fx`, `cid`,
    `cats`), no mesmo formato dos registros de `base1000` no protótipo.

    `cats` (antes `segs`, ligado a `Projeto.Segmento`) agora vem das
    categorias dos formulários que o participante de fato respondeu
    (`RespostaFormulario.formulario.categoria`) — reflete quem essa pessoa
    é de verdade (que assuntos ela já respondeu perguntas sobre), não em que
    projeto/segmento comercial ela foi recrutada.

    `cls` é o código bruto de `Participante.FaixaRendaIndividual` (A-E, ou
    `None` se ainda não preenchida) — o cliente busca o rótulo de cada
    código em `faixas_renda_disponiveis()` (ver essa função)."""
    from formularios.models import RespostaFormulario

    cats_por_participante = {}
    linhas = (
        RespostaFormulario.objects.filter(participacao__participante__in=participantes)
        .exclude(formulario__categoria__isnull=True)
        .values_list("participacao__participante_id", "formulario__categoria__nome")
        .distinct()
    )
    for participante_id, categoria_nome in linhas:
        cats_por_participante.setdefault(participante_id, set()).add(categoria_nome)

    capitais_por_nome_lower = {nome.lower(): nome for nome in CAPITAIS_PRINCIPAIS}
    hoje = timezone.localdate()

    registros = []
    for p in participantes:
        registros.append(
            {
                "uf": (p.uf or "").strip().upper(),
                "gen": p.get_genero_display(),
                "cls": p.renda_individual,
                "fx": _faixa_etaria(p.data_nascimento, hoje) if p.data_nascimento else None,
                "cid": capitais_por_nome_lower.get((p.cidade or "").strip().lower(), ""),
                "cats": sorted(cats_por_participante.get(p.id, ())),
                "prof": str(p.profissao) if p.profissao_id else "",
            }
        )
    return registros


def construir_donut(itens, centro_titulo, centro_rotulo):
    """itens: [{'label', 'count', 'cor'}, ...]. Monta o conic-gradient e a
    legenda (com contagem e percentual) pro componente `.donut`/`.donut-legend`.
    Usado só pela "Situação dos participantes" (ver docstring do módulo)."""
    total = sum(item["count"] for item in itens)
    fatias = []
    legenda = []
    angulo = 0.0
    for item in itens:
        fim = angulo + (item["count"] / total * 360 if total else 0)
        if item["count"] > 0:
            fatias.append(f"{item['cor']} {angulo:.1f}deg {fim:.1f}deg")
        angulo = fim
        pct = round(item["count"] / total * 100) if total else 0
        legenda.append({**item, "pct": pct})
    gradiente = f"conic-gradient({','.join(fatias)})" if fatias else None
    return {
        "gradiente": gradiente,
        "legenda": legenda,
        "total": total,
        "centro": f"{centro_titulo}\n{centro_rotulo}",
    }


def construir_barras_horizontais(itens, cor="linear-gradient(90deg,#FF6E8C,var(--violet))"):
    """itens: [{'label', 'count'}, ...]. Componente `.hbar-row`/`.hbar` do
    protótipo (usado lá pro "top estados") — uma linha compacta por
    categoria, sem a altura fixa e desproporcional de um canvas Chart.js.
    Usado pelo "Pipeline de captação", que não é interativo no protótipo."""
    total = sum(item["count"] for item in itens)
    maximo = max([1, *(item["count"] for item in itens)])
    barras = []
    for item in itens:
        largura = round(item["count"] / maximo * 100, 1) if item["count"] else 0
        pct = round(item["count"] / total * 100) if total else 0
        barras.append({**item, "largura": largura, "pct": pct, "cor": item.get("cor", cor)})
    return {"barras": barras, "total": total}
