from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

TEXTO_ESCOLHA_CATEGORIAS_PADRAO = (
    "Escolha 3 categorias que tem mais domínio para responder perguntas e participar de pesquisas:"
)


class Projeto(models.Model):
    class Status(models.TextChoices):
        RECRUTANDO = "RECRUTANDO", "Recrutando"
        EM_CAMPO = "EM_CAMPO", "Em campo"
        CONCLUIDO = "CONCLUIDO", "Concluído"

    nome = models.CharField(max_length=150)
    cliente = models.CharField(max_length=150)
    marca = models.CharField(max_length=150, blank=True, help_text="Ex.: Adidas.")
    metodologia = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECRUTANDO)
    # Era uma lista fixa de 5 opções no código (`Segmento`, TextChoices) — trocado por FK
    # pra `CategoriaFormulario` (cadastrada em "Configurações de Formulários › Categorias")
    # pra usar a mesma fonte da verdade que os dashboards já usam desde a rodada
    # "Segmento → Categoria" (`core/dashviz.py`), em vez de duas listas de categoria
    # divergentes no sistema.
    categoria = models.ForeignKey(
        "formularios.CategoriaFormulario",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="projetos",
    )
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
        # Participacao liga em Perfil, não direto em Projeto — import local
        # pra não criar ciclo (participacoes já importa projetos).
        from participacoes.models import Participacao

        return Participacao.objects.filter(perfil__projeto=self).count()

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


class Perfil(models.Model):
    """Um projeto tem de 1 a N perfis (ex.: "Mulheres 18-25", "Homens 25-40") —
    é o perfil, não mais o projeto direto, que carrega o(s) formulário(s) de
    coleta e recebe os participantes. Um perfil pode ter 0 a N formulários
    associados, numa ordem escolhida (`formularios`, M2M via `PerfilFormulario`
    — mesmo padrão de `Formulario`↔`Variavel`/`FormularioVariavel`).
    `"formularios.Formulario"` é referenciado por string (não por import
    direto) porque `formularios/models.py` já importa `Projeto` daqui —
    importar `Formulario` de volta criaria um ciclo."""

    class Tipo(models.TextChoices):
        CAPTACAO = "CAPTACAO", "Captação"
        RESPOSTAS = "RESPOSTAS", "Respostas"

    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name="perfis")
    nome = models.CharField(max_length=150)
    tipo = models.CharField(
        max_length=20,
        choices=Tipo.choices,
        default=Tipo.CAPTACAO,
        help_text=(
            "Captação: perfil recebe gente nova (link público, associação manual/lote). "
            "Respostas: perfil só coleta respostas de quem já foi captado antes."
        ),
    )
    formularios = models.ManyToManyField(
        "formularios.Formulario",
        through="PerfilFormulario",
        related_name="perfis",
        blank=True,
    )
    # Escolha de categorias no cadastro público (só tem efeito em perfil de
    # Captação com mais categorias de formulário do que `qtd_categorias_escolha`
    # — ver `pessoas/views.py::cadastro_publico`). Editável por perfil porque
    # o texto/quantidade pode fazer sentido diferente pra cada pesquisa.
    qtd_categorias_escolha = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1)],
        help_text=(
            "Quando este perfil é de Captação e tem mais categorias de formulário do que "
            "esse número, a pessoa escolhe essa quantidade de categorias antes de "
            "responder — só os formulários das categorias escolhidas abrem pra ela."
        ),
    )
    texto_escolha_categorias = models.CharField(
        max_length=300,
        blank=True,
        default=TEXTO_ESCOLHA_CATEGORIAS_PADRAO,
        help_text="Pergunta mostrada na tela de escolha de categorias (em branco usa o texto padrão).",
    )
    texto_boas_vindas_categorias = models.TextField(
        blank=True,
        help_text="Texto opcional mostrado acima da pergunta, na tela de escolha de categorias.",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["projeto", "nome"]
        constraints = [
            models.UniqueConstraint(fields=["projeto", "nome"], name="uniq_projeto_perfil_nome")
        ]

    def __str__(self):
        return f"{self.projeto.nome} — {self.nome}"

    @property
    def ocupadas(self):
        return self.participacoes.count()

    @property
    def texto_escolha_categorias_efetivo(self):
        """`texto_escolha_categorias` com fallback pro texto padrão quando
        vazio — deixado em branco não deveria virar um título sumido na tela
        de escolha de categorias."""
        return self.texto_escolha_categorias or TEXTO_ESCOLHA_CATEGORIAS_PADRAO

    @property
    def formularios_ordenados(self):
        """`self.formularios.all()` NÃO respeita a ordem do through
        (`PerfilFormulario.ordem`) — o M2M manager ordena pelo `Meta.ordering`
        do `Formulario` (nome), não do through. Esse é o jeito certo de
        pegar os formulários do perfil na ordem escolhida; usado tanto nas
        views quanto direto nos templates."""
        return [
            pf.formulario
            for pf in self.perfil_formularios.select_related("formulario__categoria").all()
        ]


class PerfilFormulario(models.Model):
    """Liga um Perfil aos Formularios escolhidos, com a ordem de exibição —
    mesmo papel que `formularios.FormularioVariavel` tem pra Variavel dentro
    de um Formulario."""

    perfil = models.ForeignKey(Perfil, on_delete=models.CASCADE, related_name="perfil_formularios")
    formulario = models.ForeignKey(
        "formularios.Formulario", on_delete=models.PROTECT, related_name="perfil_associacoes"
    )
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordem"]
        constraints = [
            models.UniqueConstraint(fields=["perfil", "formulario"], name="uniq_perfil_formulario")
        ]

    def __str__(self):
        return f"{self.perfil} — {self.formulario}"
