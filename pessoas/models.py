from datetime import date

from django.conf import settings
from django.db import models
from django.utils import timezone

from .validators import validar_cpf


class Profissao(models.Model):
    """Lista curada de profissões pro dropdown de cadastro — não é texto
    livre nem uma lista fixa no código, fica no banco pra dar pra
    ajustar/ampliar sem precisar de deploy. `tem_especialidade` controla se o
    formulário abre um campo de texto livre pra especialidade (ex.: Médico →
    Cardiologista) quando essa profissão é escolhida."""

    nome = models.CharField(max_length=100, unique=True)
    tem_especialidade = models.BooleanField(
        default=False, help_text="Ex.: Médico, Professor, Analista de TI — abre campo de especialidade."
    )

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Participante(models.Model):
    class UF(models.TextChoices):
        AC = "AC", "Acre"
        AL = "AL", "Alagoas"
        AP = "AP", "Amapá"
        AM = "AM", "Amazonas"
        BA = "BA", "Bahia"
        CE = "CE", "Ceará"
        DF = "DF", "Distrito Federal"
        ES = "ES", "Espírito Santo"
        GO = "GO", "Goiás"
        MA = "MA", "Maranhão"
        MT = "MT", "Mato Grosso"
        MS = "MS", "Mato Grosso do Sul"
        MG = "MG", "Minas Gerais"
        PA = "PA", "Pará"
        PB = "PB", "Paraíba"
        PR = "PR", "Paraná"
        PE = "PE", "Pernambuco"
        PI = "PI", "Piauí"
        RJ = "RJ", "Rio de Janeiro"
        RN = "RN", "Rio Grande do Norte"
        RS = "RS", "Rio Grande do Sul"
        RO = "RO", "Rondônia"
        RR = "RR", "Roraima"
        SC = "SC", "Santa Catarina"
        SP = "SP", "São Paulo"
        SE = "SE", "Sergipe"
        TO = "TO", "Tocantins"

    # Choices desta classe (Genero, Escolaridade, Renda*, Raca, EstadoCivil,
    # Ocupacao, Regiao) foram todas realinhadas com o BP.xlsx (aba "Modelo",
    # colunas H a Y) — cada aba com o nome da coluna (ex.: aba "N" pra
    # Gênero) é considerada a fonte da verdade das opções, por pedido
    # explícito do usuário ("o que temos hoje é um princípio de teste, o da
    # planilha é a versão final").
    class Genero(models.TextChoices):
        MULHER_CIS = "MULHER_CIS", "Mulher cisgênero"
        HOMEM_CIS = "HOMEM_CIS", "Homem cisgênero"
        MULHER_TRANS = "MULHER_TRANS", "Mulher transgênero"
        HOMEM_TRANS = "HOMEM_TRANS", "Homem transgênero"
        NAO_BINARIA = "NAO_BINARIA", "Pessoa não binária"
        OUTRA = "OUTRA", "Outra identidade de gênero"
        NAO_RESPONDE = "NAO_RESPONDE", "Prefiro não responder"

    class Raca(models.TextChoices):
        BRANCA = "BRANCA", "Branca"
        PRETA = "PRETA", "Preta"
        PARDA = "PARDA", "Parda"
        AMARELA = "AMARELA", "Amarela"
        INDIGENA = "INDIGENA", "Indígena"

    class EstadoCivil(models.TextChoices):
        SOLTEIRO = "SOLTEIRO", "Solteiro(a)"
        CASADO = "CASADO", "Casado(a)"
        UNIAO_ESTAVEL = "UNIAO_ESTAVEL", "União estável"
        SEPARADO = "SEPARADO", "Separado(a)"
        DIVORCIADO = "DIVORCIADO", "Divorciado(a)"
        VIUVO = "VIUVO", "Viúvo(a)"

    class Ocupacao(models.TextChoices):
        OCUPACAO_REMUNERADA = "OCUPACAO_REMUNERADA", "Ocupação remunerada"
        ESTUDANTE_E_OCUPACAO = "ESTUDANTE_E_OCUPACAO", "Estudante e ocupação remunerada"
        ESTUDANTE = "ESTUDANTE", "Estudante"
        DESEMPREGADO = "DESEMPREGADO", "Desempregado(a)"
        APOSENTADO = "APOSENTADO", "Aposentado(a)"
        ATIVIDADES_DO_LAR = "ATIVIDADES_DO_LAR", "Atividades do lar"

    class Regiao(models.TextChoices):
        NORTE = "NORTE", "Norte"
        NORDESTE = "NORDESTE", "Nordeste"
        CENTRO_OESTE = "CENTRO_OESTE", "Centro-Oeste"
        SUDESTE = "SUDESTE", "Sudeste"
        SUL = "SUL", "Sul"

    class Escolaridade(models.TextChoices):
        MEDIO_INCOMPLETO = "MEDIO_INCOMPLETO", "Ensino Médio Incompleto"
        MEDIO_COMPLETO = "MEDIO_COMPLETO", "Ensino Médio Completo"
        SUPERIOR_INCOMPLETO = "SUPERIOR_INCOMPLETO", "Ensino Superior Incompleto"
        SUPERIOR_COMPLETO = "SUPERIOR_COMPLETO", "Ensino Superior Completo"
        POS_GRADUACAO = "POS_GRADUACAO", "Pós Graduação"
        MESTRADO = "MESTRADO", "Mestrado"
        DOUTORADO = "DOUTORADO", "Doutorado"

    # Códigos A-E iguais aos da planilha ("Classe Social"), mas com rótulo
    # próprio pra cada uma — individual e familiar têm faixas de valor
    # diferentes pro mesmo código de classe.
    class FaixaRendaIndividual(models.TextChoices):
        A = "A", "A — a partir de R$ 9.738"
        B = "B", "B — R$ 4.869 a R$ 9.737"
        C = "C", "C — R$ 1.883 a R$ 4.868"
        D = "D", "D — R$ 974 a R$ 1.882"
        E = "E", "E — até R$ 973"

    class FaixaRendaFamiliar(models.TextChoices):
        A = "A", "A — 20 salários mínimos"
        B = "B", "B — 10 a 20 salários mínimos"
        C = "C", "C — 4 a 10 salários mínimos"
        D = "D", "D — 2 a 4 salários mínimos"
        E = "E", "E — até 2 salários mínimos"

    class Situacao(models.TextChoices):
        PENDENTE = "PENDENTE", "Pendente"
        APROVADO = "APROVADO", "Aprovado"
        DESCARTADO = "DESCARTADO", "Descartado"

    # Marca de onde o cadastro veio de fato — separado de `origem_recrutador`
    # (que só diz QUEM leva o crédito pela indicação, não COMO a pessoa
    # entrou no sistema). Sem isso, todo participante com `origem_recrutador`
    # preenchido aparecia como "Cadastro público" mesmo quando veio de
    # importação em lote feita pela equipe. Fica `null` em quem foi criado
    # antes desta distinção existir — não dá pra reconstruir com certeza a
    # origem de cadastros antigos.
    class OrigemCadastro(models.TextChoices):
        PUBLICO = "PUBLICO", "Cadastro público"
        IMPORTACAO_LEGADO = "IMPORTACAO_LEGADO", "Participante legado — importação"
        IMPORTACAO = "IMPORTACAO", "Importação em lote"
        MANUAL_EQUIPE = "MANUAL_EQUIPE", "Cadastro manual (equipe)"

    class FormaPagamento(models.TextChoices):
        PIX = "PIX", "PIX"
        TRANSFERENCIA = "TRANSFERENCIA", "Transferência"

    codigo = models.CharField(max_length=20, unique=True, editable=False)
    nome = models.CharField(max_length=150, db_index=True)
    # `null=True` (mas sem `blank=True`) de propósito: os formulários normais
    # continuam exigindo CPF (a obrigatoriedade neles depende de `blank`, não
    # de `null`) — só o import de lote legado, que grava direto no model sem
    # passar pelo form, usa `None` quando a planilha não trouxer CPF. Precisa
    # ser `None`, não `""`, porque o campo é `unique=True` — duas pessoas sem
    # CPF com `""` colidiriam nessa constraint; `None` não colide (regra
    # padrão de unicidade em NULL no Postgres).
    cpf = models.CharField(max_length=14, unique=True, null=True, validators=[validar_cpf])
    data_nascimento = models.DateField()
    genero = models.CharField(max_length=20, choices=Genero.choices)
    # `null=True` nos campos novos abaixo segue o mesmo padrão do CPF: são
    # obrigatórios pra qualquer cadastro passando pelo formulário normal
    # (`blank` controla isso), mas ficam `None` em quem já estava cadastrado
    # antes dessa mudança — sem precisar de uma migração de dado inventando
    # valor pra gente que nunca respondeu essas perguntas.
    raca = models.CharField(max_length=20, choices=Raca.choices, null=True)
    telefone = models.CharField(max_length=20, db_index=True)
    email = models.EmailField(db_index=True)
    cep = models.CharField(max_length=9)
    bairro = models.CharField(max_length=100)
    uf = models.CharField(max_length=2, choices=UF.choices, db_index=True)
    cidade = models.CharField(max_length=100)
    regiao = models.CharField(max_length=20, choices=Regiao.choices, null=True)
    escolaridade = models.CharField(max_length=20, choices=Escolaridade.choices)
    profissao = models.ForeignKey(
        Profissao, null=True, blank=False, on_delete=models.SET_NULL, related_name="participantes"
    )
    especialidade = models.CharField(
        max_length=150, blank=True, help_text="Só preenchido quando a profissão tem especialidade."
    )
    ocupacao = models.CharField(max_length=25, choices=Ocupacao.choices, null=True)
    estado_civil = models.CharField(max_length=20, choices=EstadoCivil.choices, null=True)
    # Faixa de renda passa a ser 2 perguntas separadas (a planilha trata como
    # duas colunas distintas, P e Q) — mesmo código de classe (A-E), rótulo
    # diferente pra cada uma.
    renda_individual = models.CharField(max_length=1, choices=FaixaRendaIndividual.choices, null=True, db_index=True)
    renda_familiar = models.CharField(max_length=1, choices=FaixaRendaFamiliar.choices, null=True)
    situacao = models.CharField(max_length=20, choices=Situacao.choices, default=Situacao.PENDENTE, db_index=True)

    cadastro_incompleto = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "Marcado automaticamente quando o cadastro veio de um lote legado sem "
            "telefone, data de nascimento, UF, cidade ou CPF — algum desses campos "
            "ficou com um valor de preenchimento (\"Não informado\"/data placeholder) "
            "em vez do dado real. Sinaliza quem precisa ser procurado pra completar o "
            "cadastro depois."
        ),
    )

    forma_pagamento = models.CharField(max_length=20, choices=FormaPagamento.choices, blank=True)
    chave_pix = models.CharField(max_length=140, blank=True)

    consentimento_lgpd = models.BooleanField(default=False)
    consentimento_versao = models.ForeignKey(
        "termos.VersaoTermo",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="participantes_aceitantes",
    )

    origem_recrutador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="participantes_indicados",
    )
    origem_cadastro = models.CharField(max_length=20, choices=OrigemCadastro.choices, null=True, blank=True)
    data_ultima_participacao = models.DateField(null=True, blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="participantes_criados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.codigo} · {self.nome}"

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self._gerar_codigo()
        super().save(*args, **kwargs)

    @staticmethod
    def _gerar_codigo():
        ano = timezone.now().year
        prefixo = f"P-{ano}-"
        ultimo = (
            Participante.objects.filter(codigo__startswith=prefixo).order_by("-codigo").first()
        )
        seq = int(ultimo.codigo.rsplit("-", 1)[-1]) + 1 if ultimo else 1
        return f"{prefixo}{seq:04d}"

    @property
    def idade(self):
        hoje = date.today()
        anos = hoje.year - self.data_nascimento.year
        if (hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day):
            anos -= 1
        return anos

    @property
    def iniciais(self):
        partes = self.nome.split()
        if len(partes) >= 2:
            return (partes[0][0] + partes[-1][0]).upper()
        return self.nome[:2].upper()

    @property
    def cor_avatar(self):
        return f"g{self.pk % 5}" if self.pk else "g0"

    @property
    def cpf_mascarado(self):
        if not self.cpf:
            return "—"
        digitos = "".join(filter(str.isdigit, self.cpf))
        if len(digitos) != 11:
            return self.cpf
        return f"***.{digitos[3:6]}.***-**"

    @property
    def telefone_mascarado(self):
        return "(**) *****-" + self.telefone[-4:] if len(self.telefone) >= 4 else "****"

    @property
    def email_mascarado(self):
        if "@" not in self.email:
            return self.email
        usuario, dominio = self.email.split("@", 1)
        return f"{usuario[:2]}***@{dominio}"
