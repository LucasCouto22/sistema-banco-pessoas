import django.db.models.deletion
from django.db import migrations, models

# Troca `Participacao.projeto` (FK direta em Projeto) por `Participacao.perfil`
# (FK em Perfil, o novo nível de segmentação dentro do projeto). Em 3
# migrações, como já foi feito nesta sessão pra `Participante.profissao`
# (CharField → FK): 1) adiciona `perfil` (nulo) ao lado de `projeto`; 2)
# RunPython copia o dado (`participacoes.0004`); 3) remove `projeto` e fecha
# `perfil` como obrigatório (`participacoes.0005`).


class Migration(migrations.Migration):
    dependencies = [
        ("participacoes", "0002_remove_avaliacao_nota_geral"),
        ("projetos", "0005_seed_perfis"),
    ]

    operations = [
        migrations.AddField(
            model_name="participacao",
            name="perfil",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="participacoes",
                to="projetos.perfil",
            ),
        ),
    ]
