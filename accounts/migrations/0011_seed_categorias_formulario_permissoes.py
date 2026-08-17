from django.db import migrations

CATALOGO = {
    "categorias_formulario.ver": ("Ver a lista de categorias de formulário", "Formulários"),
    "categorias_formulario.gerenciar": ("Criar e editar categorias de formulário", "Formulários"),
    "categorias_formulario.excluir": ("Excluir categorias de formulário", "Formulários"),
}

MATRIZ = {
    "ADMINISTRADOR": ["categorias_formulario.ver", "categorias_formulario.gerenciar", "categorias_formulario.excluir"],
    "OPERADOR": ["categorias_formulario.ver", "categorias_formulario.gerenciar", "categorias_formulario.excluir"],
    "VISUALIZADOR": ["categorias_formulario.ver"],
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
    dependencies = [("accounts", "0010_seed_exportar_permissoes")]

    operations = [migrations.RunPython(seed, remover)]
