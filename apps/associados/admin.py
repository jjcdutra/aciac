from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils.html import format_html

from .models import Associado, User

admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    fieldsets = BaseUserAdmin.fieldsets + (("Papel", {"fields": ("role",)}),)
    add_fieldsets = BaseUserAdmin.add_fieldsets + (("Papel", {"fields": ("role",)}),)


@admin.register(Associado)
class AssociadoAdmin(admin.ModelAdmin):
    list_display = (
        "matricula",
        "razao_social",
        "documento_mascarado_link",
        "status_badge",
        "cidade_uf",
        "criado_em",
    )
    list_filter = ("status", "tipo_documento", "uf")
    search_fields = ("matricula", "razao_social", "documento", "user__email")
    readonly_fields = ("matricula", "data_aprovacao", "criado_em", "atualizado_em")
    actions = ["aprovar_associados", "negar_associados", "inativar_associados"]
    date_hierarchy = "criado_em"

    fieldsets = (
        ("Identificação", {"fields": ("user", "matricula", "status", "data_aprovacao")}),
        ("Documento", {"fields": ("tipo_documento", "documento", "razao_social", "nome_fantasia", "telefone")}),
        ("Endereço", {"fields": (("logradouro", "numero"), "complemento", "bairro", ("cidade", "uf"), "cep")}),
        ("Metadados", {"fields": ("criado_em", "atualizado_em")}),
    )

    @admin.display(description="CPF/CNPJ")
    def documento_mascarado_link(self, obj):
        return obj.documento_mascarado

    @admin.display(description="Status")
    def status_badge(self, obj):
        cores = {"ativo": "green", "pendente": "orange", "inativo": "gray", "negado": "red"}
        cor = cores.get(obj.status, "black")
        return format_html(
            '<span style="color:{};font-weight:600">{}</span>', cor, obj.get_status_display()
        )

    @admin.display(description="Cidade/UF")
    def cidade_uf(self, obj):
        return f"{obj.cidade}/{obj.uf}" if obj.cidade else "—"

    @admin.action(description="Aprovar associados selecionados")
    def aprovar_associados(self, request, queryset):
        count = 0
        for obj in queryset:
            obj.status = Associado.Status.ATIVO
            obj.save()  # save() preenche data_aprovacao
            count += 1
        self.message_user(request, f"{count} associado(s) aprovado(s).")

    @admin.action(description="Negar associados selecionados")
    def negar_associados(self, request, queryset):
        updated = queryset.update(status=Associado.Status.NEGADO)
        self.message_user(request, f"{updated} associado(s) negado(s).")

    @admin.action(description="Inativar associados selecionados")
    def inativar_associados(self, request, queryset):
        updated = queryset.update(status=Associado.Status.INATIVO)
        self.message_user(request, f"{updated} associado(s) inativado(s).")
