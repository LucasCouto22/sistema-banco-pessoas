from django.db import migrations

CATALOGO = {
    "formularios.ver": ("Ver a lista de formulários", "Formulários"),
    "formularios.gerenciar": ("Criar e editar formulários (e as variáveis que cada um usa)", "Formulários"),
    "formularios.excluir": ("Excluir formulários", "Formulários"),
}

MATRIZ = {
    "ADMINISTRADOR": ["formularios.ver", "formularios.gerenciar", "formularios.excluir"],
    "OPERADOR": ["formularios.ver", "formularios.gerenciar", "formularios.excluir"],
    "VISUALIZADOR": ["formularios.ver"],
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
    dependencies = [("accounts", "0007_seed_variaveis_permissoes")]

    operations = [migrations.RunPython(seed, remover)]
