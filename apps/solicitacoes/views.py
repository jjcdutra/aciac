from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.associados.decorators import exige_aprovado
from apps.pagamentos.models import Pagamento
from apps.pagamentos.services import gerar_pagamento_pix

from .forms import SolicitarServicoForm
from .models import Servico, Solicitacao


def _servicos_ativos():
    Servico.seed_defaults()
    return Servico.objects.filter(ativo=True)


@login_required
@exige_aprovado
@require_http_methods(["GET", "POST"])
def listar_servicos(request):
    servicos = _servicos_ativos()
    form = SolicitarServicoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        servico = form.cleaned_data["servico"]
        solicitacao = Solicitacao.objects.create(
            associado=request.user,
            servico=servico,
            valor=servico.valor,
            observacoes=form.cleaned_data.get("observacoes", ""),
        )
        messages.success(
            request,
            f"Solicitação {solicitacao.protocolo} criada. Realize o pagamento PIX para prosseguir.",
        )
        return redirect("solicitacoes:pagar", protocolo=solicitacao.protocolo)
    return render(
        request,
        "solicitacoes/servicos.html",
        {"servicos": servicos, "form": form, "valor_taxa": settings.VALORES["TAXA_ASSOCIACAO"]},
    )


@login_required
@require_http_methods(["GET"])
def minhas_solicitacoes(request):
    solicitacoes = Solicitacao.objects.filter(associado=request.user).select_related("servico")
    return render(request, "solicitacoes/minhas.html", {"solicitacoes": solicitacoes})


@login_required
@require_http_methods(["GET"])
def detalhe(request, protocolo):
    solicitacao = get_object_or_404(
        Solicitacao, protocolo=protocolo, associado=request.user
    )
    pagamento = Pagamento.objects.filter(solicitacao=solicitacao).first()
    pix_payload = None
    if solicitacao.pode_pagar and pagamento:
        pix_payload = pagamento.pix_payload
    return render(
        request,
        "solicitacoes/detalhe.html",
        {"s": solicitacao, "pagamento": pagamento, "pix_payload": pix_payload},
    )


@login_required
@require_http_methods(["GET", "POST"])
def pagar(request, protocolo):
    """Exibe/gera o PIX da solicitação e permite confirmar o pagamento."""
    solicitacao = get_object_or_404(
        Solicitacao, protocolo=protocolo, associado=request.user
    )
    if not solicitacao.pode_pagar:
        return redirect("solicitacoes:detalhe", protocolo=protocolo)

    pagamento, _ = Pagamento.objects.get_or_create(
        solicitacao=solicitacao,
        defaults={
            "valor": solicitacao.valor,
            "pago": False,
        },
    )
    if not pagamento.pix_payload:
        try:
            txid = solicitacao.protocolo
            pagamento.pix_payload = gerar_pagamento_pix(
                valor=solicitacao.valor,
                txid=txid,
                descricao=f"{solicitacao.servico.nome} - {solicitacao.protocolo}",
            )
            pagamento.save(update_fields=["pix_payload"])
        except ValueError:
            messages.error(
                request,
                "Pagamento PIX indisponível no momento. "
                "Configure a chave PIX (ASSOCIACAO_PIX_CHAVE) ou contate a equipe.",
            )
            return redirect("solicitacoes:detalhe", protocolo=protocolo)

    if request.method == "POST" and request.POST.get("confirmar") == "1":
        solicitacao.status = Solicitacao.Status.EM_ANALISE
        solicitacao.save(update_fields=["status", "atualizado_em"])
        messages.success(
            request,
            "Pagamento registrado! A equipe irá confirmar e liberar sua solicitação.",
        )
        return redirect("solicitacoes:detalhe", protocolo=protocolo)

    return render(
        request,
        "solicitacoes/pagar.html",
        {"s": solicitacao, "pagamento": pagamento},
    )
