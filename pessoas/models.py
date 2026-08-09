from datetime import date

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from .validators import validar_cpf


class Participante(models.Model):
    class Genero(models.TextChoices):
        FEMININO = "FEMININO", "Feminino"
        MASCULINO = "MASCULINO", "Masculino"
        OUTRO = "OUTRO", "Outro"
        NAO_INFORMA = "NAO_INFORMA", "Prefere não informar"

    class Escolaridade(models.TextChoices):
        FUNDAMENTAL = "FUNDAMENTAL", "Fundamental"
        MEDIO = "MEDIO", "Médio"
        SUPERIOR = "SUPERIOR", "Superior"
        POS = "POS", "Pós-graduação"

    class FaixaRenda(models.TextChoices):
        A_B = "A_B", "Classes A/B"
        C = "C", "Classe C"
        D_E = "D_E", "Classes D/E"

    class Situacao(models.TextChoices):
        PENDENTE = "PENDENTE", "Pendente"
        APROVADO = "APROVADO", "Aprovado"
        DESCARTADO = "DESCARTADO", "Descartado"

    class FormaPagamento(models.TextChoices):
        PIX = "PIX", "PIX"
        TRANSFERENCIA = "TRANSFERENCIA", "Transferência"

    codigo = models.CharField(max_length=20, unique=True, editable=False)
    nome = models.CharField(max_length=150)
    cpf = models.CharField(max_length=14, unique=True, validators=[validar_cpf])
    data_nascimento = models.DateField()
    genero = models.CharField(max_length=20, choices=Genero.choices, blank=True)
    telefone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    cidade = models.CharField(max_length=100)
    uf = models.CharField(max_length=2, validators=[RegexValidator(r"^[A-Za-z]{2}$", "Use a sigla do estado (2 letras).")])
    cep = models.CharField(max_length=9, blank=True)
    escolaridade = models.CharField(max_length=20, choices=Escolaridade.choices, blank=True)
    profissao = models.CharField(max_length=100, blank=True)
    faixa_renda = models.CharField(max_length=10, choices=FaixaRenda.choices, blank=True)
    situacao = models.CharField(max_length=20, choices=Situacao.choices, default=Situacao.PENDENTE)

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
