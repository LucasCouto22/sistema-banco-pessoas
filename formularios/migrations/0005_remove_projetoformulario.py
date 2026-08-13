from django.db import migrations

# `ProjetoFormulario` (M2M projeto↔formulário) foi superado pelo campo
# `Perfil.formulario` (cada perfil carrega um formulário só) —
# `projetos.0005_seed_perfis` já leu os dados daqui pra semear os perfis
# padrão antes desta migração rodar, por isso a dependência abaixo.


class Migration(migrations.Migration):
    dependencies = [
        ("formularios", "0004_seed_tipo_texto_curto"),
        ("projetos", "0005_seed_perfis"),
    ]

    operations = [
        migrations.DeleteModel(name="ProjetoFormulario"),
    ]
