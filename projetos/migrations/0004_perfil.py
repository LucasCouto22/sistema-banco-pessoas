import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projetos', '0003_add_marca'),
        ('formularios', '0004_seed_tipo_texto_curto'),
    ]

    operations = [
        migrations.CreateModel(
            name='Perfil',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=150)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('formulario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='perfis', to='formularios.formulario')),
                ('projeto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='perfis', to='projetos.projeto')),
            ],
            options={
                'ordering': ['projeto', 'nome'],
            },
        ),
        migrations.AddConstraint(
            model_name='perfil',
            constraint=models.UniqueConstraint(fields=('projeto', 'nome'), name='uniq_projeto_perfil_nome'),
        ),
    ]
