from django.conf import settings
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.pagamentos.models import Pagamento
from apps.solicitacoes.models import Solicitacao

from .forms import CadastroForm


@require_http_methods(["GET", "POST"])
def cadastro(request):
    if request.user.is_authenticated:
        return redirect("associados:painel")

    if request.method == "POST":
        form = CadastroForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                "Cadastro recebido! Sua matrícula será liberada após aprovação "
                "pela equipe. Você já pode entrar para acompanhar o status.",
            )
            # Em produção, enviar e-mail de confirmação aqui
            return redirect("associados:login")
    else:
        form = CadastroForm()

    return render(request, "associados/cadastro.html", {"form": form})


class LoginView(auth_views.LoginView):
    template_name = "associados/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        """Admin/staff que entram pelo site vão direto para o painel /admin."""
        if self.request.user.is_staff:
            return reverse("admin:index")
        return super().get_success_url()


class LogoutView(auth_views.LogoutView):
    next_page = "core:home"


class PasswordResetView(auth_views.PasswordResetView):
    template_name = "associados/recuperar_senha.html"
    email_template_name = "registration/password_reset_email.txt"
    subject_template_name = "registration/password_reset_subject.txt"
    success_url = "/associados/recuperar-senha/enviado/"


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "associados/recuperar_senha_enviado.html"


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "associados/recuperar_senha_nova.html"
    success_url = "/associados/recuperar-senha/completado/"


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "associados/recuperar_senha_completo.html"


@login_required
@require_http_methods(["GET"])
def painel(request):
    """Dashboard do associado logado."""
    perfil = getattr(request.user, "perfil", None)
    solicitacoes = (
        Solicitacao.objects.filter(associado=request.user).order_by("-criado_em")[:10]
    )
    pagamentos = (
        Pagamento.objects.filter(solicitacao__associado=request.user).order_by("-criado_em")[:5]
    )
    context = {
        "perfil": perfil,
        "solicitacoes": solicitacoes,
        "pagamentos": pagamentos,
        "valor_taxa": settings.VALORES["TAXA_ASSOCIACAO"],
        "pendente_aprovacao": perfil and perfil.status == perfil.Status.PENDENTE,
        "aprovado": request.user.aprovado,
    }
    return render(request, "associados/painel.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def perfil(request):
    """Editar dados básicos do associado."""
    associado = getattr(request.user, "perfil", None)
    if request.method == "POST" and associado:
        for campo in ("telefone", "logradouro", "numero", "complemento", "bairro", "cidade", "uf", "cep", "nome_fantasia"):
            if campo in request.POST:
                setattr(associado, campo, request.POST[campo])
        associado.uf = (associado.uf or "").upper()[:2]
        associado.save()
        messages.success(request, "Dados atualizados com sucesso.")
        return redirect("associados:perfil")
    return render(request, "associados/perfil.html", {"associado": associado})
