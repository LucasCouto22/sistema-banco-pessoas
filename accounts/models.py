from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    class Nivel(models.TextChoices):
        ADMINISTRADOR = "ADMINISTRADOR", "Administrador"
        OPERADOR = "OPERADOR", "Operador"
        VISUALIZADOR = "VISUALIZADOR", "Visualizador"
        FREELANCER = "FREELANCER", "Freelancer"

    nivel = models.CharField(max_length=20, choices=Nivel.choices, default=Nivel.VISUALIZADOR)
    telefone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.get_full_name() or self.username

    def tem_permissao(self, codigo):
        if self.is_superuser:
            return True
        if not hasattr(self, "_permissoes_cache"):
            self._permissoes_cache = set(
                NivelPermissao.objects.filter(nivel=self.nivel, concedida=True).values_list(
                    "permissao__codigo", flat=True
                )
            )
        return codigo in self._permissoes_cache


class Permissao(models.Model):
    codigo = models.CharField(max_length=60, unique=True)
    descricao = models.CharField(max_length=140)
    grupo = models.CharField(max_length=60)

    class Meta:
        ordering = ["grupo", "codigo"]

    def __str__(self):
        return self.codigo


class NivelPermissao(models.Model):
    nivel = models.CharField(max_length=20, choices=Usuario.Nivel.choices)
    permissao = models.ForeignKey(Permissao, on_delete=models.CASCADE, related_name="niveis")
    concedida = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["nivel", "permissao"], name="uniq_nivel_permissao")
        ]
        ordering = ["nivel", "permissao__grupo", "permissao__codigo"]

    def __str__(self):
        return f"{self.nivel} · {self.permissao.codigo} · {'sim' if self.concedida else 'não'}"


# Cada tipo de aviso da sidebar tem uma permissão de nível correspondente
# (controlada no painel de permissões) e um campo correspondente em
# PreferenciaAvisos (controlado pelo próprio usuário em "Meu perfil"). Um
# aviso só aparece se as duas coisas permitirem.
TIPOS_AVISO = {
    "triagem_pendente": "avisos.triagem_pendente",
    "projetos_vagas": "avisos.projetos_vagas",
    "termos_vencendo": "avisos.termos_vencendo",
}


class PreferenciaAvisos(models.Model):
    usuario = models.OneToOneField(
        "accounts.Usuario", on_delete=models.CASCADE, related_name="preferencia_avisos"
    )
    triagem_pendente = models.BooleanField(
        default=True, verbose_name="Triagem de participantes pendente"
    )
    projetos_vagas = models.BooleanField(
        default=True, verbose_name="Projetos com vagas em aberto e campo próximo"
    )
    termos_vencendo = models.BooleanField(
        default=True, verbose_name="Termos vigentes perto de expirar"
    )

    def __str__(self):
        return f"Preferências de avisos de {self.usuario}"

    @classmethod
    def para(cls, usuario):
        preferencia, _ = cls.objects.get_or_create(usuario=usuario)
        return preferencia


class AvisoDispensado(models.Model):
    usuario = models.ForeignKey(
        "accounts.Usuario", on_delete=models.CASCADE, related_name="avisos_dispensados"
    )
    chave = models.CharField(max_length=100)
    conteudo = models.CharField(max_length=255, blank=True)
    dispensado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["usuario", "chave", "conteudo"], name="uniq_aviso_dispensado")
        ]

    def __str__(self):
        return f"{self.usuario} dispensou {self.chave}"
