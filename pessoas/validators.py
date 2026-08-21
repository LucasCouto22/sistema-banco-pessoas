import re
from datetime import datetime

from django.core.exceptions import ValidationError


def normalizar_cpf(valor):
    return re.sub(r"\D", "", valor or "")


def normalizar_telefone(valor):
    """Tira toda pontuação/espaço do telefone — o dado sempre entra como
    string, mas só com dígitos, pra uma busca por `icontains` (ou o upsert
    de lote em `matching.py::encontrar_participante_existente`) achar o
    mesmo telefone digitado com ou sem formatação diferente."""
    return re.sub(r"\D", "", valor or "")


# Formatos de data de nascimento aceitos em importação de planilha/lote
# legado — dia primeiro (padrão BR: d/m/aa, dd/m/aa, dd/mm/aa, dd/mm/aaaa...)
# tentado antes de mês primeiro (US), pra desambiguar datas onde dia e mês
# caberiam nos dois jeitos (ex.: "05/04/1990" vira 5 de abril, não 4 de
# maio). ISO ("aaaa-mm-dd") vem primeiro de todos — já é o formato que uma
# célula de data do Excel vira, e o que qualquer `<input type="date">`
# manda no POST.
_FORMATOS_DATA_NASCIMENTO = [
    "%Y-%m-%d",
    "%d/%m/%Y", "%d/%m/%y",
    "%d-%m-%Y", "%d-%m-%y",
    "%d.%m.%Y", "%d.%m.%y",
    "%m/%d/%Y", "%m/%d/%y",
]


def normalizar_data_nascimento(texto):
    """Converte uma data de nascimento em texto pra ISO (aaaa-mm-dd) —
    formato que tanto `date.fromisoformat()` quanto o `DateField` do Django
    aceitam de cara. Usada tanto na leitura da planilha
    (`pessoas/wizard_csv.py`) quanto no preparo de linha de lote legado
    (`pessoas/matching.py::preparar_linha_legado`) — os dois pontos onde uma
    data pode chegar como texto solto, não só o valor típico de célula de
    data do Excel.

    Texto que não bate com nenhum formato conhecido volta sem alteração —
    quem chama trata como "não veio data válida" do jeito que já tratava."""
    texto = (texto or "").strip()
    if not texto:
        return texto
    for formato in _FORMATOS_DATA_NASCIMENTO:
        try:
            return datetime.strptime(texto, formato).date().isoformat()
        except ValueError:
            continue
    return texto


# Formatos de data e hora completos aceitos pra "data e hora da aplicação"
# (quando a planilha traz o dia e a hora exatos da pesquisa) — tentados
# antes dos formatos "só data" e "só mês/ano" porque são mais específicos.
_FORMATOS_DATA_HORA_APLICACAO = [
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M",
    "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
    "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M",
]

# Só data (sem hora) — mesmos formatos aceitos em `_FORMATOS_DATA_NASCIMENTO`.
_FORMATOS_DATA_APLICACAO = list(_FORMATOS_DATA_NASCIMENTO)

# Só mês/ano numérico (ex.: "07/2026", "2026-07") — dia e hora completados
# com o coringa (dia 1, meia-noite) na hora de montar o resultado.
_FORMATOS_MES_ANO_APLICACAO = ["%m/%Y", "%m-%Y", "%Y-%m", "%Y/%m", "%m/%y", "%m-%y"]

# Mês por extenso/abreviado em português (ex.: "jul-2026", "julho/2026",
# "jul de 26") — é o formato que o usuário avisou que é o mais comum na
# planilha. Chaves sempre minúsculas e sem acento além do "ç"/"ã" já
# presentes na forma comum (mesmo padrão de aceitar variação usado nos
# outros mapas de texto livre do wizard, ex.: `RACA_MAP`).
_MESES_PT = {
    "jan": 1, "janeiro": 1,
    "fev": 2, "fevereiro": 2,
    "mar": 3, "marco": 3, "março": 3,
    "abr": 4, "abril": 4,
    "mai": 5, "maio": 5,
    "jun": 6, "junho": 6,
    "jul": 7, "julho": 7,
    "ago": 8, "agosto": 8,
    "set": 9, "setembro": 9,
    "out": 10, "outubro": 10,
    "nov": 11, "novembro": 11,
    "dez": 12, "dezembro": 12,
}

_REGEX_MES_NOME_ANO = re.compile(r"^([a-zçã]+)\s*(?:de\s+)?[-/\s]*(\d{2,4})$")


def _ano_de_2_digitos(aa):
    """Mesma regra do `%y` do `strptime` (00-68 → 2000-2068, 69-99 →
    1969-1999) — reaproveitada aqui porque o mês por nome não passa pelo
    `strptime` (não existe `%b` confiável pra abreviação em português)."""
    return datetime.strptime(aa, "%y").year


def normalizar_data_aplicacao(texto):
    """Converte "data e hora da aplicação" (quando a pesquisa foi de fato
    aplicada com a pessoa) em ISO (`aaaa-mm-ddThh:mm:ss`) — pronto pra
    `datetime.fromisoformat()`. Aceita data e hora completas, só data, ou só
    mês/ano (o formato mais comum avisado pelo usuário, ex.: "jul-2026",
    "07/2026") — nesse último caso completa dia e hora com valores coringa
    (dia 1, meia-noite): não dá pra saber o dia/hora exatos só com mês/ano,
    então usa o primeiro instante do mês como aproximação.

    Texto vazio ou que não bate com nenhum formato conhecido volta `""` —
    quem chama (`participacoes/views.py`/`pessoas/views.py::wizard_revisao`)
    trata como "não veio" e usa o padrão de hoje (data/hora da importação)."""
    texto = (texto or "").strip()
    if not texto:
        return ""

    for formato in _FORMATOS_DATA_HORA_APLICACAO:
        try:
            return datetime.strptime(texto, formato).isoformat()
        except ValueError:
            continue

    for formato in _FORMATOS_DATA_APLICACAO:
        try:
            data = datetime.strptime(texto, formato).date()
            return datetime(data.year, data.month, data.day).isoformat()
        except ValueError:
            continue

    for formato in _FORMATOS_MES_ANO_APLICACAO:
        try:
            data = datetime.strptime(texto, formato)
            return datetime(data.year, data.month, 1).isoformat()
        except ValueError:
            continue

    match = _REGEX_MES_NOME_ANO.match(texto.strip().lower())
    if match:
        nome_mes, ano_texto = match.groups()
        mes = _MESES_PT.get(nome_mes)
        if mes:
            ano = int(ano_texto) if len(ano_texto) == 4 else _ano_de_2_digitos(ano_texto)
            return datetime(ano, mes, 1).isoformat()

    return ""


def validar_cpf(value):
    """Valida CPF pelo algoritmo de dígito verificador (mesma regra do protótipo)."""
    cpf = re.sub(r"\D", "", value or "")
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        raise ValidationError("CPF inválido.")

    def _digito(parcial):
        soma = sum(int(d) * peso for d, peso in zip(parcial, range(len(parcial) + 1, 1, -1)))
        resto = (soma * 10) % 11
        return 0 if resto == 10 else resto

    d1 = _digito(cpf[:9])
    d2 = _digito(cpf[:9] + str(d1))
    if cpf[-2:] != f"{d1}{d2}":
        raise ValidationError("CPF inválido.")
