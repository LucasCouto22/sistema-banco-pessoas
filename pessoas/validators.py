import re
from datetime import datetime

from django.core.exceptions import ValidationError


def normalizar_cpf(valor):
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
