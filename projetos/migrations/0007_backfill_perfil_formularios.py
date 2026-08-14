from django.db import migrations


def copiar_formulario_para_m2m(apps, schema_editor):
    Perfil = apps.get_model("projetos", "Perfil")
    PerfilFormulario = apps.get_model("projetos", "PerfilFormulario")
    for perfil in Perfil.objects.exclude(formulario_id=None):
        PerfilFormulario.objects.create(perfil=perfil, formulario_id=perfil.formulario_id, ordem=0)


def reverter(apps, schema_editor):
    PerfilFormulario = apps.get_model("projetos", "PerfilFormulario")
    PerfilFormulario.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('projetos', '0006_perfilformulario'),
    ]

    operations = [
        migrations.RunPython(copiar_formulario_para_m2m, reverter),
    ]
