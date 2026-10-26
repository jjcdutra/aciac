from django.db import models


class Pagamento(models.Model):
    """Registro de pagamento PIX de uma solicitação."""

    solicitacao = models.OneToOneField(
        "solicitacoes.Solicitacao",
        on_delete=models.CASCADE,
        related_name="pagamento",
        verbose_name="solicitação",
    )
    valor = models.DecimalField("valor (R$)", max_digits=10, decimal_places=2)
    pix_payload = models.TextField("payload PIX (copia e cola)", blank=True)
    pago = models.BooleanField(default=False)
    confirmado_por = models.ForeignKey(
        "associados.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pagamentos_confirmados",
        verbose_name="confirmado por",
    )
    pago_em = models.DateTimeField("pago em", null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "pagamento"
        verbose_name_plural = "pagamentos"

    def __str__(self):
        return f"Pagamento {self.solicitacao.protocolo} — R$ {self.valor}"
