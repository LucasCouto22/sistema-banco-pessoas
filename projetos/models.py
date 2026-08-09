from django.conf import settings
from django.db import models


class Projeto(models.Model):
    class Status(models.TextChoices):
        RECRUTANDO = "RECRUTANDO", "Recrutando"
        EM_CAMPO = "EM_CAMPO", "Em campo"
        CONCLUIDO = "CONCLUIDO", "Concluído"

    class Segmento(models.TextChoices):
        SAUDE = "SAUDE", "Saúde"
        COSMETICOS = "COSMETICOS", "Cosméticos"
        ALIMENTACAO = "ALIMENTACAO", "Alimentação"
        BANCO = "BANCO", "Banco"
        TECNOLOGIA = "TECNOLOGIA", "Tecnologia"
        OUTRO = "OUTRO", "Outro"

    nome = models.CharField(max_length=150)
    cliente = models.CharField(max_length=150)
    metodologia = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECRUTANDO)
    segmento = models.CharField(max_length=20, choices=Segmento.choices, blank=True)
    data_inicio = models.DateField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)
    incentivo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valor_perfil = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vagas = models.PositiveIntegerField(default=0)
    descricao = models.TextField(blank=True)

    perfil_idade_min = models.PositiveSmallIntegerField(null=True, blank=True)
    perfil_idade_max = models.PositiveSmallIntegerField(null=True, blank=True)
    perfil_genero = models.CharField(max_length=20, blank=True)
    perfil_regiao = models.CharField(max_length=100, blank=True)
    perfil_renda = models.CharField(max_length=10, blank=True)
    perfil_criterios_livres = models.TextField(blank=True)

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="projetos_criados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return self.nome

    @property
    def ocupadas(self):
        return self.participacoes.count()

    @property
    def ocupacao_percentual(self):
        if not self.vagas:
            return 0
        return min(100, round(100 * self.ocupadas / self.vagas))

    @property
    def perfil_resumo(self):
        partes = []
        if self.perfil_idade_min and self.perfil_idade_max:
            partes.append(f"{self.perfil_idade_min}-{self.perfil_idade_max} anos")
        elif self.perfil_idade_min:
            partes.append(f"{self.perfil_idade_min}+ anos")
        elif self.perfil_idade_max:
            partes.append(f"até {self.perfil_idade_max} anos")
        if self.perfil_genero:
            partes.append(self.perfil_genero)
        if self.perfil_regiao:
            partes.append(self.perfil_regiao)
        if self.perfil_renda:
            partes.append(self.perfil_renda)
        if self.perfil_criterios_livres:
            partes.append(self.perfil_criterios_livres)
        return " · ".join(partes)
