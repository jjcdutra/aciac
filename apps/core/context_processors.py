from django.conf import settings


def identidade(request):
    """Disponibiliza a identidade da associação (do .env) em todos os templates."""
    return {"associacao": settings.ASSOCIACAO, "valores": settings.VALORES}
