from django.conf import settings
from django.db import models


class Termo(models.Model):
    class Tipo(models.TextChoices):
        CONSENTIMENTO = "CONSENTIMENTO", "Termo de Consentimento"
        CONTRATO = "CONTRATO", "Contrato"
        CONFIDENCIALIDADE = "CONFIDENCIALIDADE", "Termo de Confidencialidade"
        CESSAO_IMAGEM_VOZ = "CESSAO_IMAGEM_VOZ", "Cessão de Imagem e Voz"

    nome = models.CharField(max_length=150)
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    @property
    def versao_vigente(self):
        return self.versoes.filter(status=VersaoTermo.Status.VIGENTE).order_by("-publicado_em").first()

    def proxima_versao(self):
        from django.utils import timezone

        ano = timezone.now().year
        prefixo = f"v{ano}."
        ultima = self.versoes.filter(versao__startswith=prefixo).order_by("-versao").first()
        seq = int(ultima.versao.rsplit(".", 1)[-1]) + 1 if ultima else 1
        return f"{prefixo}{seq}"


class VersaoTermo(models.Model):
    class Status(models.TextChoices):
        VIGENTE = "VIGENTE", "Vigente"
        SUBSTITUIDA = "SUBSTITUIDA", "Substituída"
        AGENDADA = "AGENDADA", "Agendada"
        EXPIRADA = "EXPIRADA", "Expirada"

    termo = models.ForeignKey(Termo, on_delete=models.CASCADE, related_name="versoes")
    versao = models.CharField(max_length=20)
    texto = models.TextField()
    inicio_vigencia = models.DateField()
    fim_vigencia = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.VIGENTE)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="versoes_publicadas"
    )
    publicado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-publicado_em"]
        constraints = [
            models.UniqueConstraint(fields=["termo", "versao"], name="uniq_termo_versao")
        ]

    def __str__(self):
        return f"{self.termo.nome} · {self.versao}"

    @property
    def aceites(self):
        return self.participantes_aceitantes.count()


class LogAlteracao(models.Model):
    versao = models.ForeignKey(VersaoTermo, on_delete=models.CASCADE, related_name="logs")
    quando = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    acao = models.CharField(max_length=200)

    class Meta:
        ordering = ["-quando"]

    def __str__(self):
        return f"{self.quando} · {self.acao}"
