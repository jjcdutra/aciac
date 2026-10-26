from django.contrib import admin
from django.utils import timezone

from .models import Pagamento


@admin.register(Pagamento)
class PagamentoAdmin(admin.ModelAdmin):
    list_display = ("solicitacao", "valor", "pago_badge", "pago_em", "criado_em")
    list_filter = ("pago",)
    search_fields = ("solicitacao__protocolo", "solicitacao__associado__email")
    readonly_fields = ("pix_payload", "criado_em", "atualizado_em")
    actions = ["confirmar_pagamentos"]
    date_hierarchy = "criado_em"

    @admin.display(description="Pago", boolean=True)
    def pago_badge(self, obj):
        return obj.pago

    @admin.action(description="Confirmar pagamentos selecionados (marcar como pago)")
    def confirmar_pagamentos(self, request, queryset):
        from apps.solicitacoes.models import Solicitacao

        count = 0
        for pag in queryset.select_related("solicitacao"):
            pag.pago = True
            pag.pago_em = timezone.now()
            pag.confirmado_por = request.user
            pag.save(update_fields=["pago", "pago_em", "confirmado_por", "atualizado_em"])
            sol = pag.solicitacao
            sol.status = Solicitacao.Status.APROVADO
            sol.pago_em = pag.pago_em
            sol.save(update_fields=["status", "pago_em", "atualizado_em"])
            count += 1
        self.message_user(request, f"{count} pagamento(s) confirmado(s).")
