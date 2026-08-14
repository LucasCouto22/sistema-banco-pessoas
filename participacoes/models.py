from django.conf import settings
from django.db import models
from django.utils import timezone

from pessoas.models import Participante
from projetos.models import Perfil


class Participacao(models.Model):
    class Etapa(models.TextChoices):
        # Ordem do funil: Preenchimento de Dados é o ponto de entrada de quem
        # se cadastra pelo link público (`pessoas/views.py::cadastro_publico`)
        # — só depois disso a equipe analisa o perfil.
        PREENCHIMENTO_DADOS = "PREENCHIMENTO_DADOS", "Preenchimento de Dados"
        ANALISE_PERFIL = "ANALISE_PERFIL", "Análise de Perfil"
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

    # Cor do badge por status — agrupado por "sentimento" do resultado, não
    # 1 cor por valor: Aprovação (positivo) e Backup (neutro/reserva) têm
    # cor própria; Desistência e Não aprovado dividem o vermelho (os dois
    # tiram a pessoa do funil por um motivo "forte"); Não compareceu fica
    # em âmbar (mais leve, pode ser reagendado); Fora do perfil em cinza
    # (nem chegou a ser avaliado — não é uma rejeição de qualidade).
    CORES_STATUS = {
        Status.APROVACAO: "b-green",
        Status.BACKUP: "b-blue",
        Status.DESISTENCIA: "b-red",
        Status.NAO_COMPARECEU: "b-amber",
        Status.NAO_APROVADO: "b-red",
        Status.FORA_PERFIL: "b-gray",
    }

    # Mesmas cores usadas no gráfico "Situação dos participantes" dos
    # dashboards (ver `core/dashviz.py::COR_ETAPA`) — mantidas em paralelo
    # porque lá o consumo é direto em CSS var pro Chart.js, aqui é classe de
    # badge, mas o mapeamento cor↔etapa é o mesmo pra não destoar visualmente.
    CORES_ETAPA = {
        Etapa.PREENCHIMENTO_DADOS: "b-violet",
        Etapa.ANALISE_PERFIL: "b-blue",
        Etapa.CAPTACAO_MATERIAL: "b-amber",
        Etapa.ENTREVISTA: "b-pink",
        Etapa.PAGO: "b-green",
    }

    ETAPAS_ORDEM = [
        Etapa.PREENCHIMENTO_DADOS,
        Etapa.ANALISE_PERFIL,
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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # "Pago" é a última etapa do funil — só quando chega ali dá pra
        # dizer que a pessoa participou de verdade (fez a pesquisa e foi
        # paga), então é o gatilho certo pra atualizar a "última
        # participação" dela no Banco de Pessoas. Roda em todo save (não só
        # em `avancar_etapa`) pra também cobrir quem já tiver o campo
        # ausente por ter chegado em "Pago" antes dessa lógica existir.
        if self.etapa == self.Etapa.PAGO:
            hoje = timezone.localdate()
            Participante.objects.filter(pk=self.participante_id).exclude(
                data_ultima_participacao=hoje
            ).update(data_ultima_participacao=hoje)

    @property
    def status_badge(self):
        return self.CORES_STATUS.get(self.status, "b-gray")

    @property
    def etapa_badge(self):
        return self.CORES_ETAPA.get(self.etapa, "b-gray")

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
