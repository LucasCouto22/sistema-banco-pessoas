"""A migração 0008 (`0008_campos_perfilamento_bp.py`) trocou as opções de
`Participante.genero` de 4 códigos (FEMININO/MASCULINO/OUTRO/NAO_INFORMA,
alinhados só a masculino/feminino/outro) pras 7 do BP.xlsx (MULHER_CIS/
HOMEM_CIS/MULHER_TRANS/HOMEM_TRANS/NAO_BINARIA/OUTRA/NAO_RESPONDE) via
`AlterField` — que só muda a lista de opções válidas pro Django, não toca
nos dados já gravados. Participantes cadastrados antes dessa migração
ficaram com o código antigo, que não bate com nenhuma opção atual: não
aparecem em nenhuma barra/legenda de "Gênero" nos dashboards (o valor
salvo simplesmente não corresponde a nada que a tela sabe desenhar).

Essa migração corrige esses registros pro código novo mais próximo —
mapeamento direto do binário antigo pro equivalente cisgênero (não havia
pergunta sobre esse recorte no cadastro antigo, cisgênero é o padrão mais
razoável pra "Feminino"/"Masculino" sem mais contexto), e "Outro"/"Prefere
não informar" pros equivalentes novos."""

from django.db import migrations

MAPA_GENERO_LEGADO = {
    "FEMININO": "MULHER_CIS",
    "MASCULINO": "HOMEM_CIS",
    "OUTRO": "OUTRA",
    "NAO_INFORMA": "NAO_RESPONDE",
}


def corrigir_genero_legado(apps, schema_editor):
    Participante = apps.get_model("pessoas", "Participante")
    for codigo_antigo, codigo_novo in MAPA_GENERO_LEGADO.items():
        Participante.objects.filter(genero=codigo_antigo).update(genero=codigo_novo)


def reverter(apps, schema_editor):
    # Não reversível de forma exata — se algum desses registros já foi
    # editado depois (agora com um código novo "de verdade"), não dá pra
    # distinguir do que foi corrigido aqui. Deixa como está.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("pessoas", "0009_cep_obrigatorio"),
    ]

    operations = [
        migrations.RunPython(corrigir_genero_legado, reverter),
    ]
