from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.associados.decorators import exige_aprovado

from .forms import ConsultaForm
from .models import ConsultaLog
from .services import _hash_documento, consultar_cnpj, consultar_cpf
from .validators import only_digits, tipo_documento_de


def _client_ip(request) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


def _rate_limit_excedido(ip: str) -> bool:
    limite = settings.CONSULTA["RATE_LIMIT"]
    agora = timezone.now()
    janela_inicio = agora.timestamp() - 60
    key = f"consulta-rl:{ip}"
    entradas = cache.get(key) or []
    entradas = [t for t in entradas if t >= janela_inicio]
    if len(entradas) >= limite:
        return True
    entradas.append(agora.timestamp())
    cache.set(key, entradas, timeout=70)
    return False


def _cache_get(documento: str):
    from django.core.cache import cache as c

    return c.get(f"consulta:{documento}")


def _cache_set(documento: str, payload: dict):
    horas = settings.CONSULTA["CACHE_HORAS"]
    cache.set(f"consulta:{documento}", payload, timeout=horas * 3600)


def _registrar_log(ip: str, tipo: str, documento: str, sucesso: bool):
    ConsultaLog.objects.create(
        ip=ip,
        tipo=tipo,
        documento_hash=_hash_documento(documento),
        sucesso=sucesso,
    )


def _executar_consulta(documento: str) -> dict:
    """Cache-first, senão consulta a API externa."""
    cached = _cache_get(documento)
    if cached:
        return cached

    tipo = tipo_documento_de(documento)
    if tipo == "CNPJ":
        payload = consultar_cnpj(documento)
    else:
        payload = consultar_cpf(documento)

    payload["_consultado_em"] = timezone.now().isoformat()
    payload["_cache"] = False
    _cache_set(documento, payload)
    return payload


@login_required
@exige_aprovado
@require_http_methods(["GET", "POST"])
def consulta(request):
    resultado = None
    erro = None
    form = ConsultaForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        ip = _client_ip(request)
        if _rate_limit_excedido(ip):
            erro = "Muitas consultas neste minuto. Aguarde um instante e tente novamente."
        else:
            documento = form.cleaned_data["documento"]
            try:
                resultado = _executar_consulta(documento)
                resultado["_cache"] = bool(_cache_get(documento))
                _registrar_log(ip, tipo_documento_de(documento), documento, sucesso=True)
            except NotImplementedError as e:
                erro = str(e)
                _registrar_log(ip, tipo_documento_de(documento), documento, sucesso=False)
            except Exception:
                erro = (
                    "Não foi possível consultar agora. Verifique o número ou tente novamente "
                    "em instantes."
                )
                _registrar_log(ip, tipo_documento_de(documento), documento, sucesso=False)

    return render(
        request,
        "consultas/consulta.html",
        {
            "form": form,
            "resultado": resultado,
            "erro": erro,
            "rate_limit": settings.CONSULTA["RATE_LIMIT"],
        },
    )


@login_required
@require_http_methods(["POST"])
def consulta_ajax(request):
    """Endpoint JSON para consulta via JS (mesma lógica + rate-limit)."""
    if not request.user.aprovado:
        return JsonResponse(
            {"ok": False, "erro": "Serviço liberado após a aprovação do seu cadastro."},
            status=403,
        )
    form = ConsultaForm(request.POST or request.GET)
    if not form.is_valid():
        return JsonResponse({"ok": False, "erro": "Documento inválido.", "campo": "documento"}, status=400)

    ip = _client_ip(request)
    if _rate_limit_excedido(ip):
        return JsonResponse(
            {"ok": False, "erro": "Muitas consultas neste minuto."},
            status=429,
        )

    documento = form.cleaned_data["documento"]
    try:
        payload = _executar_consulta(documento)
        payload["ok"] = True
        payload.pop("_consultado_em", None)
        _registrar_log(ip, tipo_documento_de(documento), documento, sucesso=True)
        return JsonResponse(payload)
    except NotImplementedError as e:
        return JsonResponse({"ok": False, "erro": str(e)}, status=501)
    except Exception:
        return JsonResponse(
            {"ok": False, "erro": "Falha na consulta. Tente novamente."},
            status=502,
        )
