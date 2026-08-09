from django.conf import settings
from django.db import models


class RegistroAcesso(models.Model):
    class Acao(models.TextChoices):
        VISUALIZACAO = "VISUALIZACAO", "Visualização"
        PAGAMENTO = "PAGAMENTO", "Pagamento"
        ALTERACAO = "ALTERACAO", "Alteração"

    quando = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="registros_auditoria"
    )
    titular = models.CharField(max_length=20, help_text="Código do participante (titular dos dados)")
    acao = models.CharField(max_length=20, choices=Acao.choices)
    detalhe = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-quando"]

    def __str__(self):
        return f"{self.quando} · {self.usuario} · {self.acao}"


def registrar(usuario, titular, acao, detalhe=""):
    return RegistroAcesso.objects.create(usuario=usuario, titular=titular, acao=acao, detalhe=detalhe)
