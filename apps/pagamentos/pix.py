"""
Geração de payload PIX (BR Code EMV) — implementação própria, sem dependências.

Estrutura conforme manual do Banco Central:
  00  Payload Format Indicator
  01  Point of Initiation Method (12 = dinâmico/uso único)
  26  Merchant Account Information (chave PIX)
  52  Merchant Category Code
  53  Transaction Currency (986 = BRL)
  54  Transaction Amount
  58  Country Code (BR)
  59  Merchant Name
  60  Merchant City
  62  Additional Data (TXID)
  63  CRC16
"""

import unicodedata

from django.conf import settings


def _crc16_emv(data: str) -> str:
    """CRC16-CCITT-FALSE (poly 0x1021, init 0xFFFF) sobre os bytes ASCII."""
    crc = 0xFFFF
    for byte in data.encode("ascii"):
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def _sanitizar_campo(texto: str, max_len: int) -> str:
    """Remove acentos e limita o tamanho (padrão BCB: nome/cidade ≤ 25)."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.upper().strip()[:max_len]


def _tlv(id_campo: str, valor: str) -> str:
    """Tag-Length-Value: ID (2) + tamanho (2, zero-pad) + valor (máx. 99)."""
    if len(valor) > 99:
        raise ValueError(f"Campo EMV {id_campo} excede 99 caracteres ({len(valor)}).")
    return f"{id_campo}{len(valor):02d}{valor}"


def gerar_payload_pix(
    *,
    chave: str,
    nome_merchant: str,
    cidade_merchant: str,
    valor: float | str | None = None,
    txid: str = "***",
    descricao: str = "",
) -> str:
    """Monta o payload copia-e-cola (string EMV) do PIX."""
    if not chave:
        raise ValueError(
            "Chave PIX não configurada. Defina ASSOCIACAO_PIX_CHAVE no .env."
        )

    merchant_name = _sanitizar_campo(nome_merchant, 25) or "ASSOCIACAO"
    merchant_city = _sanitizar_campo(cidade_merchant, 15) or "SAO PAULO"
    txid_limpo = (txid or "***").upper()[:25]
    txid_limpo = "".join(c for c in txid_limpo if c.isalnum() or c in "-_ ") or "***"

    # 26 — Merchant Account Information (orçamento: GUI + chave + descrição ≤ 99)
    gui = _tlv("00", "br.gov.bcb.pix")
    chave_tlv = _tlv("01", chave)
    # Descrição precisa caber em 99 - len(gui) - len(chave) - 4 (tag 02 + tamanho)
    budget_desc = 99 - len(gui) - len(chave_tlv) - 4
    desc_sanitizada = _sanitizar_campo(descricao, max(0, budget_desc)) if descricao else ""
    desc_tlv = _tlv("02", desc_sanitizada) if desc_sanitizada else ""
    merchant_account = gui + chave_tlv + desc_tlv
    if len(merchant_account) > 99:
        merchant_account = gui + chave_tlv  # fallback: sem descrição

    payload = (
        _tlv("00", "01")  # Payload Format Indicator
        + _tlv("01", "12")  # Point of Initiation (uso único)
        + _tlv("26", merchant_account)
        + _tlv("52", "0000")  # MCC
        + _tlv("53", "986")  # BRL
    )
    if valor is not None and str(valor).strip() != "":
        valor_fmt = f"{float(valor):.2f}"
        payload += _tlv("54", valor_fmt)
    payload += (
        _tlv("58", "BR")
        + _tlv("59", merchant_name)
        + _tlv("60", merchant_city)
        + _tlv("62", _tlv("05", txid_limpo))  # Additional data field template
    )
    payload += _tlv("63", _crc16_emv(payload + "6304"))
    return payload


def gerar_payload_de_associacao(valor, txid: str, descricao: str = "") -> str:
    """Atalho usando a configuração do .env (ASSOCIACAO_*)."""
    conf = settings.ASSOCIACAO
    return gerar_payload_pix(
        chave=conf["PIX_CHAVE"],
        nome_merchant=conf["NOME"],
        cidade_merchant=conf["CIDADE"],
        valor=valor,
        txid=txid,
        descricao=descricao,
    )
