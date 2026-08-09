from django.db import migrations

CATALOGO = {
    "termos.ver": ("Ver termos, contratos e o histórico de versões", "Termos e Contratos"),
    "termos.gerenciar": ("Criar documentos e publicar novas versões (imutáveis)", "Termos e Contratos"),
}

MATRIZ_ADICIONAL = {
    "ADMINISTRADOR": ["termos.ver", "termos.gerenciar"],
    "OPERADOR": ["termos.ver"],
    "VISUALIZADOR": ["termos.ver"],
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
    dependencies = [("accounts", "0002_seed_permissoes")]

    operations = [migrations.RunPython(seed, remover)]
