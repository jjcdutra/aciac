from django.shortcuts import render


def home(request):
    from apps.solicitacoes.models import Servico

    Servico.seed_defaults()
    servicos = Servico.objects.filter(ativo=True)
    return render(request, "core/home.html", {"servicos": servicos})


def sobre(request):
    return render(request, "core/sobre.html")


def contato(request):
    enviado = False
    if request.method == "POST":
        # Formulário simples de contato — em produção, conectar a e-mail/serviço.
        enviado = True
    return render(request, "core/contato.html", {"enviado": enviado})


def servicos(request):
    from apps.solicitacoes.models import Servico

    Servico.seed_defaults()
    servicos_qs = Servico.objects.filter(ativo=True)
    return render(request, "core/servicos.html", {"servicos": servicos_qs})
