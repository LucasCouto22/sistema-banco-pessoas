import uuid

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.text import slugify

from participacoes.models import Participacao

# Códigos de tipo de resposta que exigem uma lista de opções cadastradas —
# usado tanto na validação do formulário de variável quanto no template pra
# decidir se mostra o bloco de opções.
CODIGOS_COM_OPCOES = {"select", "radio", "multipla_escolha"}


class TipoResposta(models.Model):
    """Catálogo dos formatos de resposta possíveis pra uma variável (texto,
    inteiro, select, etc). É uma tabela editável no banco (não um TextChoices
    fixo no código, diferente dos outros catálogos do sistema) por decisão
    explícita: dá pra cadastrar um tipo novo sem deploy — só não vai ter
    renderização/validação própria enquanto ninguém escrever o código de
    suporte pra ele, então isso é responsabilidade de quem cadastra."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=30, unique=True)
    descricao = models.CharField(max_length=100)

    class Meta:
        ordering = ["descricao"]

    def __str__(self):
        return self.descricao

    @property
    def usa_opcoes(self):
        return self.codigo in CODIGOS_COM_OPCOES


class Variavel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=150)
    chave = models.CharField(max_length=100, unique=True, editable=False)
    tipo_resposta = models.ForeignKey(TipoResposta, on_delete=models.PROTECT, related_name="variaveis")
    obrigatoria = models.BooleanField(default=False)
    ativa = models.BooleanField(default=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="variaveis_criadas",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.chave:
            self.chave = self._gerar_chave()
        super().save(*args, **kwargs)

    def _gerar_chave(self):
        base = slugify(self.nome, allow_unicode=False).replace("-", "_") or "variavel"
        candidata = base
        sufixo = 2
        while Variavel.objects.filter(chave=candidata).exclude(pk=self.pk).exists():
            candidata = f"{base}_{sufixo}"
            sufixo += 1
        return candidata


class VariavelOpcao(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    variavel = models.ForeignKey(Variavel, on_delete=models.CASCADE, related_name="opcoes")
    valor = models.CharField(max_length=150)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordem", "valor"]

    def __str__(self):
        return self.valor


class Formulario(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    inclui_campos_fixos = models.BooleanField(default=True)
    ativo = models.BooleanField(default=True)
    variaveis = models.ManyToManyField(
        Variavel, through="FormularioVariavel", related_name="formularios", blank=True
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="formularios_criados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class FormularioVariavel(models.Model):
    """Liga um Formulario às Variaveis escolhidas, com a ordem de exibição."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    formulario = models.ForeignKey(Formulario, on_delete=models.CASCADE, related_name="formulario_variaveis")
    variavel = models.ForeignKey(Variavel, on_delete=models.PROTECT, related_name="formulario_variaveis")
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordem"]
        constraints = [
            models.UniqueConstraint(fields=["formulario", "variavel"], name="uniq_formulario_variavel")
        ]

    def __str__(self):
        return f"{self.formulario} · {self.variavel}"


class RespostaFormulario(models.Model):
    """Respostas de uma participação (participante × perfil) ao formulário
    daquele perfil. Fica ligada à Participacao (não direto a
    participante+perfil) porque a Participacao já é a chave única desse par
    no sistema — evita duplicar a mesma restrição em outro lugar."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participacao = models.ForeignKey(
        Participacao, on_delete=models.CASCADE, related_name="respostas_formularios"
    )
    formulario = models.ForeignKey(Formulario, on_delete=models.PROTECT, related_name="respostas")
    # DjangoJSONEncoder (em vez do encoder padrão) sabe serializar Decimal e date/datetime
    # direto — os dois tipos que os campos "decimal" e "data" produzem no formulário
    # dinâmico de resposta (ver formularios/respostas.py).
    respostas_variaveis = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)
    criado_em = models.DateTimeField(auto_now_add=True)
    respondido_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-respondido_em"]
        constraints = [
            models.UniqueConstraint(fields=["participacao", "formulario"], name="uniq_participacao_formulario")
        ]
        indexes = [GinIndex(fields=["respostas_variaveis"], name="idx_respostas_variaveis_gin")]

    def __str__(self):
        return f"{self.participacao} · {self.formulario}"
