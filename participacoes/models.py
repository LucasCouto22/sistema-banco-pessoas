from django.conf import settings
from django.db import models

from pessoas.models import Participante
from projetos.models import Perfil


class Participacao(models.Model):
    class Etapa(models.TextChoices):
        ANALISE_PERFIL = "ANALISE_PERFIL", "Análise de Perfil"
        PREENCHIMENTO_DADOS = "PREENCHIMENTO_DADOS", "Preenchimento de Dados"
        CAPTACAO_MATERIAL = "CAPTACAO_MATERIAL", "Captação de Material"
        ENTREVISTA = "ENTREVISTA", "Entrevista"
        PAGO = "PAGO", "Pago"

    class Status(models.TextChoices):
        APROVACAO = "APROVACAO", "Aprovação"
        BACKUP = "BACKUP", "Backup"
        DESISTENCIA = "DESISTENCIA", "Desistência"
        NAO_COMPARECEU = "NAO_COMPARECEU", "Não compareceu"
        NAO_APROVADO = "NAO_APROVADO", "Não aprovado"
        FORA_PERFIL = "FORA_PERFIL", "Fora do perfil"

    ETAPAS_ORDEM = [
        Etapa.ANALISE_PERFIL,
        Etapa.PREENCHIMENTO_DADOS,
        Etapa.CAPTACAO_MATERIAL,
        Etapa.ENTREVISTA,
        Etapa.PAGO,
    ]

    participante = models.ForeignKey(Participante, on_delete=models.CASCADE, related_name="participacoes")
    perfil = models.ForeignKey(Perfil, on_delete=models.CASCADE, related_name="participacoes")
    etapa = models.CharField(max_length=30, choices=Etapa.choices, default=Etapa.ANALISE_PERFIL)
    status = models.CharField(max_length=20, choices=Status.choices, blank=True)
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="participacoes_responsavel",
    )
    observacao = models.TextField(blank=True)
    etapa_atualizada_em = models.DateTimeField(auto_now=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        constraints = [
            models.UniqueConstraint(fields=["participante", "perfil"], name="uniq_participante_perfil")
        ]

    def __str__(self):
        return f"{self.participante} · {self.perfil} · {self.get_etapa_display()}"

    def avancar_etapa(self):
        idx = self.ETAPAS_ORDEM.index(self.etapa)
        if idx >= len(self.ETAPAS_ORDEM) - 1:
            return False
        self.etapa = self.ETAPAS_ORDEM[idx + 1]
        self.save(update_fields=["etapa", "etapa_atualizada_em"])
        return True


class Avaliacao(models.Model):
    participacao = models.OneToOneField(Participacao, on_delete=models.CASCADE, related_name="avaliacao")
    comunicacao = models.PositiveSmallIntegerField()
    pontualidade = models.PositiveSmallIntegerField()
    repertorio = models.PositiveSmallIntegerField()
    comentario = models.TextField(blank=True)
    avaliado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="avaliacoes_feitas"
    )
    avaliado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Avaliação de {self.participacao} — nota {self.nota_geral}"

    @property
    def nota_geral(self):
        """Nota final não é digitada — é sempre a média dos 3 quesitos.
        Uma casa decimal, então uma combinação como 5+4+4 vira "4.3", não
        arredonda pra um número inteiro que esconderia a diferença entre,
        por exemplo, 4+4+4 e 5+4+3 (as duas dariam "4" se arredondasse)."""
        return round((self.comunicacao + self.pontualidade + self.repertorio) / 3, 1)
