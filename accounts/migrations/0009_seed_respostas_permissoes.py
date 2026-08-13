from django.db import migrations

CATALOGO = {
    "respostas.ver": ("Ver as respostas de formulário de uma participação", "Formulários"),
    "respostas.preencher": ("Preencher e editar respostas de formulário de uma participação", "Formulários"),
}

MATRIZ = {
    "ADMINISTRADOR": ["respostas.ver", "respostas.preencher"],
    "OPERADOR": ["respostas.ver", "respostas.preencher"],
    "VISUALIZADOR": ["respostas.ver"],
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
    dependencies = [("accounts", "0008_seed_formularios_permissoes")]

    operations = [migrations.RunPython(seed, remover)]
