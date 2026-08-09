from django.contrib.auth.hashers import make_password
from django.db import migrations

MATRIZ = {
    "ADMINISTRADOR": [
        "participantes.ver",
        "participantes.gerenciar",
        "participantes.revelar_pii",
        "projetos.ver",
        "projetos.gerenciar",
        "participacoes.ver",
        "participacoes.mover_etapa",
        "avaliacao.criar",
        "pagamento.ver",
        "usuarios.gerenciar",
        "permissoes.gerenciar",
        "auditoria.ver",
    ],
    "OPERADOR": [
        "participantes.ver",
        "participantes.gerenciar",
        "participantes.revelar_pii",
        "projetos.ver",
        "projetos.gerenciar",
        "participacoes.ver",
        "participacoes.mover_etapa",
    ],
    "VISUALIZADOR": [
        "participantes.ver",
        "projetos.ver",
        "participacoes.ver",
    ],
    "FREELANCER": [
        "projetos.ver",
        "participacoes.ver",
        "avaliacao.criar",
    ],
}

DEMO_USERS = [
    ("admin_demo", "Administradora", "Demo", "ADMINISTRADOR"),
    ("operador_demo", "Operador", "Demo", "OPERADOR"),
    ("visualizador_demo", "Visualizadora", "Demo", "VISUALIZADOR"),
    ("freelancer_demo", "Freelancer", "Demo", "FREELANCER"),
]

SENHA_DEMO = "QualyVortice#2026"


def seed(apps, schema_editor):
    from accounts.permissions import CATALOGO_PERMISSOES

    Permissao = apps.get_model("accounts", "Permissao")
    NivelPermissao = apps.get_model("accounts", "NivelPermissao")
    Usuario = apps.get_model("accounts", "Usuario")

    permissao_por_codigo = {}
    for codigo, descricao, grupo in CATALOGO_PERMISSOES:
        permissao, _ = Permissao.objects.get_or_create(
            codigo=codigo, defaults={"descricao": descricao, "grupo": grupo}
        )
        permissao_por_codigo[codigo] = permissao

    for nivel, codigos in MATRIZ.items():
        for codigo in codigos:
            NivelPermissao.objects.get_or_create(
                nivel=nivel,
                permissao=permissao_por_codigo[codigo],
                defaults={"concedida": True},
            )

    senha_hash = make_password(SENHA_DEMO)
    for username, primeiro, ultimo, nivel in DEMO_USERS:
        Usuario.objects.get_or_create(
            username=username,
            defaults={
                "first_name": primeiro,
                "last_name": ultimo,
                "email": f"{username}@qualyvortice.com.br",
                "nivel": nivel,
                "password": senha_hash,
                "is_active": True,
            },
        )


def remover(apps, schema_editor):
    Usuario = apps.get_model("accounts", "Usuario")
    Usuario.objects.filter(username__in=[u[0] for u in DEMO_USERS]).delete()
    NivelPermissao = apps.get_model("accounts", "NivelPermissao")
    NivelPermissao.objects.all().delete()
    Permissao = apps.get_model("accounts", "Permissao")
    Permissao.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [migrations.RunPython(seed, remover)]
