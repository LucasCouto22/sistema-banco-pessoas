from django.db import migrations

CATALOGO = {
    "avisos.triagem_pendente": ("Receber aviso de triagem de participantes pendente", "Avisos"),
    "avisos.projetos_vagas": ("Receber aviso de projetos com vagas e campo próximo", "Avisos"),
    "avisos.termos_vencendo": ("Receber aviso de termos vigentes perto de expirar", "Avisos"),
}

MATRIZ = {
    "ADMINISTRADOR": ["avisos.triagem_pendente", "avisos.projetos_vagas", "avisos.termos_vencendo"],
    "OPERADOR": ["avisos.triagem_pendente", "avisos.projetos_vagas"],
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
    dependencies = [("accounts", "0005_preferenciaavisos_avisodispensado")]

    operations = [migrations.RunPython(seed, remover)]
