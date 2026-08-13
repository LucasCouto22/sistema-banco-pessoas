from django.db import migrations

NOME_PERFIL_PADRAO = "Perfil único"


def seed(apps, schema_editor):
    """Cada Projeto existente ganha um Perfil padrão pra receber as
    Participacao/ProjetoFormulario que ele já tinha antes dessa mudança —
    `participacoes.0004` (que roda depois desta) usa esse Perfil pra
    realocar as participações antigas, que hoje ainda apontam pro Projeto
    direto. Se o projeto já tinha algum ProjetoFormulario (M2M
    projeto↔formulário, removido logo depois disso), o formulário de menor
    `ordem` vira o formulário desse perfil — os demais (quando havia mais de
    um) não são migrados; dá pra criar perfis extras manualmente pra eles."""
    Projeto = apps.get_model("projetos", "Projeto")
    Perfil = apps.get_model("projetos", "Perfil")
    ProjetoFormulario = apps.get_model("formularios", "ProjetoFormulario")

    for projeto in Projeto.objects.all():
        primeiro_vinculo = (
            ProjetoFormulario.objects.filter(projeto=projeto).order_by("ordem").first()
        )
        Perfil.objects.get_or_create(
            projeto=projeto,
            nome=NOME_PERFIL_PADRAO,
            defaults={"formulario_id": primeiro_vinculo.formulario_id if primeiro_vinculo else None},
        )


def reverter(apps, schema_editor):
    Perfil = apps.get_model("projetos", "Perfil")
    Perfil.objects.filter(nome=NOME_PERFIL_PADRAO).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("projetos", "0004_perfil"),
        ("formularios", "0004_seed_tipo_texto_curto"),
    ]

    operations = [migrations.RunPython(seed, reverter)]
