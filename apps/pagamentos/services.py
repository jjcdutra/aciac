"""Camada de serviço dos pagamentos."""

from .pix import gerar_payload_de_associacao


def gerar_pagamento_pix(*, valor, txid: str, descricao: str = "") -> str:
    """Gera o payload copia-e-cola usando a chave do .env."""
    return gerar_payload_de_associacao(valor=valor, txid=txid, descricao=descricao)
