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


class AceiteTermo(models.Model):
    """Registro de auditoria de um aceite de termo — não confundir com
    `Participante.consentimento_versao` (que só guarda a versão *atual*
    aceita, sobrescrevível). Este aqui é um log imutável, um registro por
    aceite, com o suficiente pra provar numa auditoria LGPD que a pessoa
    (ou o operador em nome dela) realmente aceitou aquela versão específica,
    quando e de onde."""

    class Origem(models.TextChoices):
        PUBLICO = "PUBLICO", "Cadastro público (a própria pessoa aceitou)"
        STAFF = "STAFF", "Registrado por um operador do sistema"

    participante = models.ForeignKey(
        "pessoas.Participante", on_delete=models.CASCADE, related_name="aceites_termos"
    )
    versao = models.ForeignKey(VersaoTermo, on_delete=models.PROTECT, related_name="aceites_registrados")
    origem = models.CharField(max_length=10, choices=Origem.choices)
    aceito_em = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    # Quem operou a tela no momento do aceite — o próprio recrutador/operador
    # que gerou o link, no caso de PUBLICO (a pessoa que aceitou não tem
    # login); quem estava logado fazendo o cadastro, no caso de STAFF.
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="aceites_termos_registrados",
    )

    class Meta:
        ordering = ["-aceito_em"]

    def __str__(self):
        return f"{self.participante} · {self.versao} · {self.aceito_em}"


def registrar_aceite(participante, versao, origem, request=None, registrado_por=None):
    """Grava um `AceiteTermo`. Não faz nada se `versao` for None (ex.: ainda
    não existe nenhuma versão vigente do termo de consentimento cadastrada) —
    sem versão não tem o que auditar."""
    if versao is None:
        return None

    from core.request_utils import ip_cliente

    ip = ip_cliente(request) if request is not None else None
    user_agent = request.META.get("HTTP_USER_AGENT", "")[:255] if request is not None else ""
    return AceiteTermo.objects.create(
        participante=participante,
        versao=versao,
        origem=origem,
        ip=ip,
        user_agent=user_agent,
        registrado_por=registrado_por,
    )
