from django import forms


class ConsultaForm(forms.Form):
    """Formulário único para CPF ou CNPJ."""

    documento = forms.CharField(
        label="CPF ou CNPJ",
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "placeholder": "000.000.000-00 ou 00.000.000/0000-00",
                "data-mask": "documento",
                "autocomplete": "off",
                "autofocus": True,
            }
        ),
    )

    def clean_documento(self):
        from apps.consultas.validators import only_digits, validar_cpf_cnpj

        raw = only_digits(self.cleaned_data["documento"])
        validar_cpf_cnpj(raw)
        return raw
