from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class RegistroAcesso(models.Model):
    class Acao(models.TextChoices):
        VISUALIZACAO = "VISUALIZACAO", "Visualização"
        PAGAMENTO = "PAGAMENTO", "Pagamento"
        ALTERACAO = "ALTERACAO", "Alteração"

    quando = models.DateTimeField(auto_now_add=True, db_index=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="registros_auditoria"
    )
    titular = models.CharField(max_length=20, help_text="Código do participante (titular dos dados)", db_index=True)
    acao = models.CharField(max_length=20, choices=Acao.choices, db_index=True)
    detalhe = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-quando"]

    def __str__(self):
        return f"{self.quando} · {self.usuario} · {self.acao}"


def registrar(usuario, titular, acao, detalhe=""):
    return RegistroAcesso.objects.create(usuario=usuario, titular=titular, acao=acao, detalhe=detalhe)


class DownloadRegistro(models.Model):
    """Marca cada exportação (PDF/XLSX) de uma base inteira feita por um
    usuário — usado só pra aplicar o limite de 1 download a cada 12h por
    usuário e por área (`tipo`), independente do formato escolhido. Não é
    sobre auditoria de acesso a um titular específico (isso é o
    `RegistroAcesso`) — é sobre limitar exportação em massa."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="downloads_em_massa"
    )
    tipo = models.CharField(max_length=30, help_text="Ex.: 'pessoas', 'participacoes'")
    quando = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-quando"]

    def __str__(self):
        return f"{self.quando} · {self.usuario} · {self.tipo}"


def verificar_limite_download(usuario, tipo, horas=12):
    """Devolve (pode_baixar, libera_em). Se `pode_baixar` for False,
    `libera_em` é o horário em que o usuário poderá baixar de novo."""
    ultimo = DownloadRegistro.objects.filter(usuario=usuario, tipo=tipo).order_by("-quando").first()
    if not ultimo:
        return True, None
    libera_em = ultimo.quando + timedelta(hours=horas)
    if timezone.now() >= libera_em:
        return True, None
    return False, libera_em


def registrar_download(usuario, tipo):
    return DownloadRegistro.objects.create(usuario=usuario, tipo=tipo)
