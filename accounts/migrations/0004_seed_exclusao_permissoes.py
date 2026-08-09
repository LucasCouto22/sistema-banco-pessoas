from django.db import migrations

CATALOGO = {
    "participantes.excluir": ("Excluir participantes", "Banco de Pessoas"),
    "projetos.excluir": ("Excluir projetos", "Projetos"),
    "participacoes.excluir": ("Remover participações do pipeline", "Participações"),
    "usuarios.excluir": ("Excluir usuários do sistema", "Administração"),
}

MATRIZ_ADICIONAL = {
    "ADMINISTRADOR": ["participantes.excluir", "projetos.excluir", "participacoes.excluir", "usuarios.excluir"],
    "OPERADOR": ["participantes.excluir", "projetos.excluir", "participacoes.excluir"],
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

    for nivel, codigos in MATRIZ_ADICIONAL.items():
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
    dependencies = [("accounts", "0003_seed_termos_permissoes")]

    operations = [migrations.RunPython(seed, remover)]
