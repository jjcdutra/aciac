"""Cliente das APIs externas de consulta (BrasilAPI / provider CPF plugável)."""

import hashlib

import httpx
from django.conf import settings

BRASILAPI_CNPJ = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
TIMEOUT = 8.0


def _hash_documento(doc: str) -> str:
    return hashlib.sha256(doc.encode()).hexdigest()


def consultar_cnpj(cnpj: str) -> dict:
    """Consulta CNPJ na BrasilAPI (gratuita, sem chave)."""
    url = BRASILAPI_CNPJ.format(cnpj=cnpj)
    resp = httpx.get(url, timeout=TIMEOUT, follow_redirects=True)
    resp.raise_for_status()
    data = resp.json()
    return {
        "tipo": "cnpj",
        "cnpj": data.get("cnpj", cnpj),
        "razao_social": data.get("razao_social", ""),
        "nome_fantasia": data.get("nome_fantasia") or "",
        "situacao": data.get("descricao_situacao_cadastral") or data.get("situacao", ""),
        "abertura": data.get("data_inicio_atividade", ""),
        "cnae": f"{data.get('cnae_fiscal', '')} — {data.get('cnae_fiscal_descricao', '')}".strip(" —"),
        "logradouro": data.get("logradouro", ""),
        "numero": data.get("numero", ""),
        "complemento": data.get("complemento") or "",
        "bairro": data.get("bairro", ""),
        "municipio": data.get("municipio", ""),
        "uf": data.get("uf", ""),
        "cep": data.get("cep", ""),
        "telefone": " ".join(filter(None, [data.get("ddd_telefone_1", ""), data.get("telefone_1", "")])),
        "capital_social": data.get("capital_social"),
        "qsa": [
            {
                "nome": s.get("nome_socio", ""),
                "qualificacao": s.get("qualificacao_socio", ""),
            }
            for s in (data.get("qsa") or [])[:15]
        ],
        "fonte": "BrasilAPI (dados abertos Receita Federal)",
    }


def consultar_cpf(cpf: str) -> dict:
    """
    Consulta CPF.

    Dados de pessoa física NÃO são públicos. Este método só funciona se a
    associação contratar um provider autorizado (ex.: API Serpro) e configurar
    SERPRO_API_TOKEN/SERPRO_API_URL no .env.
    """
    token = settings.CONSULTA.get("SERPRO_API_TOKEN", "")
    base = settings.CONSULTA.get("SERPRO_API_URL", "")
    if not token or not base:
        raise NotImplementedError(
            "Consulta de CPF requer provider autorizado. "
            "Configure SERPRO_API_TOKEN e SERPRO_API_URL no .env."
        )
    url = base.format(cpf=cpf) if "{cpf}" in base else f"{base.rstrip('/')}/{cpf}"
    resp = httpx.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT,
        follow_redirects=True,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "tipo": "cpf",
        "cpf": cpf,
        "nome": data.get("nome", ""),
        "nascimento": data.get("nascimento", ""),
        "situacao": data.get("situacao", ""),
        "fonte": "Provider autorizado (Serpro)",
    }
