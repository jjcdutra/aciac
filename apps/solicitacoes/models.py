from decimal import Decimal

from django.conf import settings
from django.db import models


class Servico(models.Model):
    """Catálogo de serviços oferecidos pela associação."""

    class Slug(models.TextChoices):
        TAXA_ASSOCIACAO = "taxa-associancao", "Taxa de associação"
        CERTIFICADO = "certificado-digital", "Certificado Digital"
        CONSULTORIA = "consultoria", "Consultoria"
        OUTROS = "outros", "Outros"

    nome = models.CharField(max_length=120)
    slug = models.SlugField(unique=True, max_length=50)
    descricao = models.TextField(blank=True)
    valor = models.DecimalField("valor (R$)", max_digits=10, decimal_places=2)
    ativo = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordem", "nome"]
        verbose_name = "serviço"
        verbose_name_plural = "serviços"

    def __str__(self):
        return self.nome

    @classmethod
    def seed_defaults(cls):
        """Cria serviços padrão a partir do .env se ainda não existirem."""
        defaults = [
            {
                "slug": cls.Slug.TAXA_ASSOCIACAO,
                "nome": "Taxa anual de associação",
                "descricao": "Regularização e manutenção da filiação à associação.",
                "valor": Decimal(str(settings.VALORES["TAXA_ASSOCIACAO"])),
            },
            {
                "slug": cls.Slug.CERTIFICADO,
                "nome": "Certificado Digital (e-CNPJ)",
                "descricao": "Emissão de certificado digital ICP-Brasil para empresas.",
                "valor": Decimal(str(settings.VALORES["CERTIFICADO_DIGITAL"])),
            },
        ]
        for item in defaults:
            cls.objects.get_or_create(slug=item["slug"], defaults=item)


class Solicitacao(models.Model):
    """Pedido de serviço feito por um associado, com máquina de status."""

    class Status(models.TextChoices):
        AGUARDANDO_PAGAMENTO = "aguardando_pagamento", "Aguardando pagamento"
        EM_ANALISE = "em_analise", "Em análise"
        APROVADO = "aprovado", "Aprovado"
        EM_ANDAMENTO = "em_andamento", "Em andamento"
        CONCLUIDO = "concluido", "Concluído"
        CANCELADO = "cancelado", "Cancelado"

    associado = models.ForeignKey(
        "associados.User",
        on_delete=models.CASCADE,
        related_name="solicitacoes",
        verbose_name="associado",
    )
    servico = models.ForeignKey(
        Servico,
        on_delete=models.PROTECT,
        related_name="solicitacoes",
        verbose_name="serviço",
    )
    valor = models.DecimalField("valor (R$)", max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.AGUARDANDO_PAGAMENTO,
    )
    observacoes = models.TextField("observações", blank=True)
    protocolo = models.CharField(max_length=20, unique=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    pago_em = models.DateTimeField("pago em", null=True, blank=True)
    concluido_em = models.DateTimeField("concluído em", null=True, blank=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "solicitação"
        verbose_name_plural = "solicitações"

    def __str__(self):
        return f"{self.protocolo} — {self.servico}"

    def save(self, *args, **kwargs):
        if not self.protocolo:
            ultimo = Solicitacao.objects.order_by("-id").first()
            numero = (ultimo.id or 0) + 1 if ultimo else 1
            self.protocolo = f"SOL{numero:06d}"
        if not self.valor:
            self.valor = self.servico.valor
        super().save(*args, **kwargs)

    @property
    def pode_pagar(self):
        return self.status == self.Status.AGUARDANDO_PAGAMENTO

    @property
    def cor_status(self):
        cores = {
            "aguardando_pagamento": "amarelo",
            "em_analise": "azul",
            "aprovado": "verde-claro",
            "em_andamento": "azul",
            "concluido": "verde",
            "cancelado": "vermelho",
        }
        return cores.get(self.status, "cinza")
