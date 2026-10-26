from django.contrib import admin

from .models import ConsultaLog


@admin.register(ConsultaLog)
class ConsultaLogAdmin(admin.ModelAdmin):
    list_display = ("criado_em", "tipo", "ip", "sucesso", "documento_hash_curto")
    list_filter = ("tipo", "sucesso")
    search_fields = ("ip", "documento_hash")
    readonly_fields = ("ip", "tipo", "documento_hash", "sucesso", "criado_em")
    date_hierarchy = "criado_em"
    actions = None

    @admin.display(description="Hash")
    def documento_hash_curto(self, obj):
        return f"{obj.documento_hash[:12]}…"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
