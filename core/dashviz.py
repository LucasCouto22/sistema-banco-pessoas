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


def dados_participantes_dashboard(participantes):
    """Um registro compacto por participante — só os campos que o dashboard
    interativo usa pra filtrar e contar (`uf`, `gen`, `cls`, `fx`, `cid`,
    `segs`), no mesmo formato dos registros de `base1000` no protótipo."""
    from participacoes.models import Participacao
    from projetos.models import Projeto

    rotulos_segmento = dict(Projeto.Segmento.choices)
    segs_por_participante = {}
    linhas = (
        Participacao.objects.filter(participante__in=participantes)
        .exclude(perfil__projeto__segmento="")
        .exclude(perfil__projeto__segmento=Projeto.Segmento.OUTRO)
        .values_list("participante_id", "perfil__projeto__segmento")
        .distinct()
    )
    for participante_id, segmento in linhas:
        segs_por_participante.setdefault(participante_id, set()).add(rotulos_segmento[segmento])

    capitais_por_nome_lower = {nome.lower(): nome for nome in CAPITAIS_PRINCIPAIS}
    hoje = timezone.localdate()

    registros = []
    for p in participantes:
        registros.append(
            {
                "uf": (p.uf or "").strip().upper(),
                "gen": p.get_genero_display(),
                "cls": p.get_renda_individual_display(),
                "fx": _faixa_etaria(p.data_nascimento, hoje) if p.data_nascimento else None,
                "cid": capitais_por_nome_lower.get((p.cidade or "").strip().lower(), ""),
                "segs": sorted(segs_por_participante.get(p.id, ())),
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
