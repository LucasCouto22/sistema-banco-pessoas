import re

from django.core.exceptions import ValidationError


def normalizar_cpf(valor):
    return re.sub(r"\D", "", valor or "")


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
