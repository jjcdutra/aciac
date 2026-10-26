from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Pagamento


@login_required
def listar(request):
    pagamentos = (
        Pagamento.objects.filter(solicitacao__associado=request.user)
        .select_related("solicitacao", "solicitacao__servico")
        .order_by("-criado_em")
    )
    return render(request, "pagamentos/listar.html", {"pagamentos": pagamentos})
