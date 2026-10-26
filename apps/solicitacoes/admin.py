from django.contrib import admin
from django.utils import timezone

from .models import Servico, Solicitacao


@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ("nome", "slug", "valor", "ativo", "ordem")
    list_editable = ("valor", "ativo", "ordem")
    prepopulated_fields = {"slug": ("nome",)}
    search_fields = ("nome", "descricao")


@admin.register(Solicitacao)
class SolicitacaoAdmin(admin.ModelAdmin):
    list_display = (
        "protocolo",
        "servico",
        "associado_email",
        "valor",
        "status_badge",
        "criado_em",
    )
    list_filter = ("status", "servico")
    search_fields = ("protocolo", "associado__email", "associado__first_name")
    readonly_fields = ("protocolo", "criado_em", "atualizado_em", "pago_em", "concluido_em")
    actions = ["aprovar", "iniciar", "concluir", "cancelar"]
    date_hierarchy = "criado_em"

    fieldsets = (
        ("Identificação", {"fields": ("protocolo", "associado", "servico", "valor", "status")}),
        ("Detalhes", {"fields": ("observacoes",)}),
        ("Datas", {"fields": ("criado_em", "atualizado_em", "pago_em", "concluido_em")}),
    )

    @admin.display(description="Associado")
    def associado_email(self, obj):
        return obj.associado.email or obj.associado.username

    @admin.display(description="Status")
    def status_badge(self, obj):
        cores = {
            "aguardando_pagamento": "orange",
            "em_analise": "#1976d2",
            "aprovado": "#388e3c",
            "em_andamento": "#0288d1",
            "concluido": "green",
            "cancelado": "gray",
        }
        cor = cores.get(obj.status, "black")
        return f'<span style="color:{cor};font-weight:600">{obj.get_status_display()}</span>'

    status_badge.short_description = "Status"
    status_badge.allow_tags = True

    def _mudar_status(self, request, queryset, novo_status):
        agora = timezone.now()
        extra = {}
        if novo_status == Solicitacao.Status.CONCLUIDO:
            extra["concluido_em"] = agora
        updated = queryset.update(status=novo_status, atualizado_em=agora, **extra)
        self.message_user(request, f"{updated} solicitação(ões) → {novo_status}.")

    @admin.action(description="Aprovar")
    def aprovar(self, request, queryset):
        self._mudar_status(request, queryset, Solicitacao.Status.APROVADO)

    @admin.action(description="Iniciar")
    def iniciar(self, request, queryset):
        self._mudar_status(request, queryset, Solicitacao.Status.EM_ANDAMENTO)

    @admin.action(description="Concluir")
    def concluir(self, request, queryset):
        self._mudar_status(request, queryset, Solicitacao.Status.CONCLUIDO)

    @admin.action(description="Cancelar")
    def cancelar(self, request, queryset):
        self._mudar_status(request, queryset, Solicitacao.Status.CANCELADO)
