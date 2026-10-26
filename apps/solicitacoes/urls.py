from django.urls import path

from . import views

app_name = "solicitacoes"

urlpatterns = [
    path("", views.listar_servicos, name="servicos"),
    path("minhas/", views.minhas_solicitacoes, name="minhas"),
    path("<slug:protocolo>/", views.detalhe, name="detalhe"),
    path("<slug:protocolo>/pagar/", views.pagar, name="pagar"),
]
