import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("participacoes", "0004_migrar_projeto_para_perfil")]

    operations = [
        migrations.RemoveConstraint(
            model_name="participacao",
            name="uniq_participante_projeto",
        ),
        migrations.RemoveField(
            model_name="participacao",
            name="projeto",
        ),
        migrations.AlterField(
            model_name="participacao",
            name="perfil",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="participacoes",
                to="projetos.perfil",
            ),
        ),
        migrations.AddConstraint(
            model_name="participacao",
            constraint=models.UniqueConstraint(fields=("participante", "perfil"), name="uniq_participante_perfil"),
        ),
    ]
