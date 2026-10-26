from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """Usuário customizado. Papel `associado` acessa o painel."""

    class Role(models.TextChoices):
        ASSOCIADO = "associado", "Associado"
        STAFF = "staff", "Equipe"

    role = models.CharField(
        "papel",
        max_length=20,
        choices=Role.choices,
        default=Role.ASSOCIADO,
    )

    @property
    def is_associado(self):
        return self.role == self.Role.ASSOCIADO or self.is_superuser

    @property
    def aprovado(self):
        """True se o cadastro do associado foi aprovado (status ativo)."""
        if self.is_superuser:
            return True
        perfil = getattr(self, "perfil", None)
        return perfil is not None and perfil.status == Associado.Status.ATIVO

    def __str__(self):
        return self.get_full_name() or self.username


class Associado(models.Model):
    """Perfil do associado, ligado ao User."""

    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente de aprovação"
        ATIVO = "ativo", "Ativo"
        INATIVO = "inativo", "Inativo"
        NEGADO = "negado", "Negado"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="perfil",
        verbose_name="usuário",
    )
    tipo_documento = models.CharField(
        "tipo de documento",
        max_length=4,
        choices=[("CPF", "CPF"), ("CNPJ", "CNPJ")],
        default="CPF",
    )
    documento = models.CharField("CPF/CNPJ", max_length=20, unique=True)
    razao_social = models.CharField("nome / razão social", max_length=255)
    nome_fantasia = models.CharField("nome fantasia", max_length=255, blank=True)
    telefone = models.CharField("telefone", max_length=20, blank=True)
    logradouro = models.CharField("logradouro", max_length=255, blank=True)
    numero = models.CharField("número", max_length=20, blank=True)
    complemento = models.CharField("complemento", max_length=100, blank=True)
    bairro = models.CharField("bairro", max_length=100, blank=True)
    cidade = models.CharField("cidade", max_length=100, blank=True)
    uf = models.CharField("UF", max_length=2, blank=True)
    cep = models.CharField("CEP", max_length=9, blank=True)
    matricula = models.CharField("matrícula", max_length=20, unique=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
    )
    data_aprovacao = models.DateTimeField("aprovado em", null=True, blank=True)
    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "associado"
        verbose_name_plural = "associados"

    def __str__(self):
        return f"{self.razao_social} ({self.documento})"

    def save(self, *args, **kwargs):
        if not self.matricula:
            ultimo = Associado.objects.order_by("-id").first()
            numero = (ultimo.id or 0) + 1 if ultimo else 1
            self.matricula = f"ASS{numero:06d}"
        if self.status == self.Status.ATIVO and not self.data_aprovacao:
            self.data_aprovacao = timezone.now()
        super().save(*args, **kwargs)

    @property
    def documento_mascarado(self):
        d = self.documento
        if self.tipo_documento == "CPF" and len(d) == 11:
            return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
        if self.tipo_documento == "CNPJ" and len(d) == 14:
            return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
        return d
