from django.db import migrations

CODIGO = "texto_curto"
DESCRICAO = "Texto curto (uma linha)"


def seed(apps, schema_editor):
    TipoResposta = apps.get_model("formularios", "TipoResposta")
    TipoResposta.objects.get_or_create(codigo=CODIGO, defaults={"descricao": DESCRICAO})


def remover(apps, schema_editor):
    TipoResposta = apps.get_model("formularios", "TipoResposta")
    TipoResposta.objects.filter(codigo=CODIGO).delete()


class Migration(migrations.Migration):
    dependencies = [("formularios", "0003_alter_respostaformulario_respostas_variaveis")]

    operations = [migrations.RunPython(seed, remover)]
