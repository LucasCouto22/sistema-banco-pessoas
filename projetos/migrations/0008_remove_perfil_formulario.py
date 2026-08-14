from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('projetos', '0007_backfill_perfil_formularios'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='perfil',
            name='formulario',
        ),
    ]
