from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def exige_aprovado(view):
    """Libera a view apenas para associados com cadastro aprovado (ativo)."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.aprovado:
            messages.warning(
                request,
                "Este serviço é liberado após a aprovação do seu cadastro.",
            )
            return redirect("associados:painel")
        return view(request, *args, **kwargs)

    return wrapper
