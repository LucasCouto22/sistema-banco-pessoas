from django.db import migrations

NOME_PERFIL_PADRAO = "Perfil único"


def migrar(apps, schema_editor):
    Participacao = apps.get_model("participacoes", "Participacao")
    Perfil = apps.get_model("projetos", "Perfil")

    perfil_padrao_por_projeto = {
        p.projeto_id: p.id for p in Perfil.objects.filter(nome=NOME_PERFIL_PADRAO)
    }
    for participacao in Participacao.objects.all():
        participacao.perfil_id = perfil_padrao_por_projeto.get(participacao.projeto_id)
        participacao.save(update_fields=["perfil"])


def reverter(apps, schema_editor):
    Participacao = apps.get_model("participacoes", "Participacao")
    Participacao.objects.update(perfil=None)


class Migration(migrations.Migration):
    dependencies = [("participacoes", "0003_add_perfil_fk")]

    operations = [migrations.RunPython(migrar, reverter)]
