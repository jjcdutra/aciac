"""Validadores de CPF/CNPJ (algoritmo dos dígitos verificadores mod-11)."""

import re

from django.core.exceptions import ValidationError

DIGITS_ONLY = re.compile(r"\D")


def only_digits(value: str) -> str:
    return DIGITS_ONLY.sub("", value or "")


def is_valid_cpf(cpf: str) -> bool:
    cpf = only_digits(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for pos in (9, 10):
        soma = sum(int(cpf[i]) * ((pos + 1) - i) for i in range(pos))
        digito = (soma * 10) % 11
        digito = 0 if digito == 10 else digito
        if digito != int(cpf[pos]):
            return False
    return True


def is_valid_cnpj(cnpj: str) -> bool:
    cnpj = only_digits(cnpj)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    for pos in (12, 13):
        soma = 0
        peso = 5 if pos == 12 else 6
        for i in range(pos):
            soma += int(cnpj[i]) * peso
            peso = peso - 1 if peso > 2 else 9
        resto = soma % 11
        digito = 0 if resto < 2 else 11 - resto
        if digito != int(cnpj[pos]):
            return False
    return True


def validar_cpf(value):
    if not is_valid_cpf(value):
        raise ValidationError("CPF inválido. Verifique os dígitos.")


def validar_cnpj(value):
    if not is_valid_cnpj(value):
        raise ValidationError("CNPJ inválido. Verifique os dígitos.")


def validar_cpf_cnpj(value):
    """Valida CPF ou CNPJ conforme o tamanho."""
    d = only_digits(value)
    if len(d) == 11:
        validar_cpf(d)
    elif len(d) == 14:
        validar_cnpj(d)
    else:
        raise ValidationError("Informe um CPF (11 dígitos) ou CNPJ (14 dígitos).")


def tipo_documento_de(value) -> str:
    d = only_digits(value)
    return "CPF" if len(d) == 11 else "CNPJ"
