from django import forms
from django.contrib.auth.forms import UserCreationForm

from apps.consultas.validators import only_digits, tipo_documento_de, validar_cpf_cnpj

from .models import Associado, User


class CadastroForm(UserCreationForm):
    """Cadastro público de novo associado."""

    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={"placeholder": "seu@email.com.br", "autocomplete": "email"}),
    )
    documento = forms.CharField(
        label="CPF ou CNPJ",
        max_length=20,
        help_text="Somente números. Usado para login e identificação.",
        widget=forms.TextInput(attrs={"placeholder": "000.000.000-00", "data-mask": "documento"}),
    )
    razao_social = forms.CharField(
        label="Nome completo / Razão social",
        max_length=255,
        widget=forms.TextInput(attrs={"placeholder": "Seu nome ou razão social"}),
    )
    nome_fantasia = forms.CharField(
        label="Nome fantasia (opcional)",
        max_length=255,
        required=False,
    )
    telefone = forms.CharField(
        label="Telefone / WhatsApp",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "(11) 99999-9999", "data-mask": "telefone"}),
    )
    logradouro = forms.CharField(label="Logradouro", max_length=255, required=False)
    numero = forms.CharField(label="Número", max_length=20, required=False)
    bairro = forms.CharField(label="Bairro", max_length=100, required=False)
    cidade = forms.CharField(label="Cidade", max_length=100, required=False)
    uf = forms.CharField(label="UF", max_length=2, required=False)
    cep = forms.CharField(label="CEP", max_length=9, required=False)
    aceite_termos = forms.BooleanField(
        label="Li e aceito os termos de uso e a política de privacidade.",
        required=True,
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Nome de usuário"
        self.fields["username"].widget.attrs.update(
            {"placeholder": "sera usado para entrar", "autocomplete": "username"}
        )
        self.fields["password1"].label = "Senha"
        self.fields["password2"].label = "Confirmar senha"
        for campo in self.fields.values():
            if campo.widget.__class__.__name__ == "TextInput":
                campo.widget.attrs.setdefault("class", "form-input")
            elif campo.widget.__class__.__name__ == "PasswordInput":
                campo.widget.attrs.setdefault("class", "form-input")
            elif campo.widget.__class__.__name__ == "EmailInput":
                campo.widget.attrs.setdefault("class", "form-input")
            elif campo.widget.__class__.__name__ == "CheckboxInput":
                campo.widget.attrs.setdefault("class", "form-checkbox")

    def clean_documento(self):
        raw = self.cleaned_data["documento"]
        if Associado.objects.filter(documento=only_digits(raw)).exists():
            raise forms.ValidationError("Já existe um associado com este CPF/CNPJ.")
        validar_cpf_cnpj(raw)
        return only_digits(raw)

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Já existe um usuário com este e-mail.")
        return email

    def clean_uf(self):
        return (self.cleaned_data.get("uf") or "").upper()[:2]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.role = User.Role.ASSOCIADO
        if commit:
            user.save()
            documento = self.cleaned_data["documento"]
            Associado.objects.create(
                user=user,
                tipo_documento=tipo_documento_de(documento),
                documento=documento,
                razao_social=self.cleaned_data["razao_social"],
                nome_fantasia=self.cleaned_data.get("nome_fantasia", ""),
                telefone=self.cleaned_data.get("telefone", ""),
                logradouro=self.cleaned_data.get("logradouro", ""),
                numero=self.cleaned_data.get("numero", ""),
                bairro=self.cleaned_data.get("bairro", ""),
                cidade=self.cleaned_data.get("cidade", ""),
                uf=self.cleaned_data.get("uf", ""),
                cep=self.cleaned_data.get("cep", ""),
            )
        return user
