from django.db import migrations

CATALOGO = {
    "variaveis.ver": ("Ver a lista de variáveis", "Variáveis"),
    "variaveis.gerenciar": ("Criar e editar variáveis", "Variáveis"),
    "variaveis.excluir": ("Excluir variáveis", "Variáveis"),
}

MATRIZ = {
    "ADMINISTRADOR": ["variaveis.ver", "variaveis.gerenciar", "variaveis.excluir"],
    "OPERADOR": ["variaveis.ver", "variaveis.gerenciar", "variaveis.excluir"],
    "VISUALIZADOR": ["variaveis.ver"],
}


def seed(apps, schema_editor):
    Permissao = apps.get_model("accounts", "Permissao")
    NivelPermissao = apps.get_model("accounts", "NivelPermissao")

    permissao_por_codigo = {}
    for codigo, (descricao, grupo) in CATALOGO.items():
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


def remover(apps, schema_editor):
    Permissao = apps.get_model("accounts", "Permissao")
    Permissao.objects.filter(codigo__in=list(CATALOGO.keys())).delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0006_seed_avisos_permissoes")]

    operations = [migrations.RunPython(seed, remover)]
