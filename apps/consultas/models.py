from django.db import models


class ConsultaLog(models.Model):
    """Auditoria + base para rate-limit de consultas."""

    class Tipo(models.TextChoices):
        CPF = "cpf", "CPF"
        CNPJ = "cnpj", "CNPJ"

    ip = models.GenericIPAddressField()
    tipo = models.CharField(max_length=4, choices=Tipo.choices)
    documento_hash = models.CharField(max_length=64, help_text="SHA-256 do documento (não guarda o número cru).")
    sucesso = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        indexes = [models.Index(fields=["ip", "criado_em"])]

    def __str__(self):
        return f"{self.get_tipo_display()} via {self.ip} — {'ok' if self.sucesso else 'erro'}"
