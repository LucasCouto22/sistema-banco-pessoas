from django.db import migrations

TIPOS = [
    ("texto", "Texto livre"),
    ("inteiro", "Número inteiro"),
    ("decimal", "Número decimal"),
    ("booleano", "Sim/Não"),
    ("data", "Data"),
    ("select", "Seleção única (dropdown)"),
    ("radio", "Seleção única (radio button)"),
    ("multipla_escolha", "Seleção múltipla (checkbox)"),
]


def seed(apps, schema_editor):
    TipoResposta = apps.get_model("formularios", "TipoResposta")
    for codigo, descricao in TIPOS:
        TipoResposta.objects.get_or_create(codigo=codigo, defaults={"descricao": descricao})


def remover(apps, schema_editor):
    TipoResposta = apps.get_model("formularios", "TipoResposta")
    TipoResposta.objects.filter(codigo__in=[codigo for codigo, _ in TIPOS]).delete()


class Migration(migrations.Migration):
    dependencies = [("formularios", "0001_initial")]

    operations = [migrations.RunPython(seed, remover)]
