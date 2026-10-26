from django import forms

from .models import Servico, Solicitacao


class SolicitarServicoForm(forms.Form):
    servico = forms.ModelChoiceField(
        queryset=Servico.objects.filter(ativo=True),
        label="Serviço",
        empty_label="Selecione o serviço",
    )
    observacoes = forms.CharField(
        label="Observações (opcional)",
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 3, "placeholder": "Detalhes, referências, prazos..."}
        ),
    )
