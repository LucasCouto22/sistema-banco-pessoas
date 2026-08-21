from django.db import migrations


def reordenar_opcoes_alfabetico(apps, schema_editor):
    # Mesma regra que passa a valer daqui pra frente em
    # `formularios/views.py::_reordenar_opcoes_alfabetico` — aplicada uma vez
    # aqui pra corrigir o `ordem` de opção já cadastrada (hoje reflete só a
    # ordem de importação/preenchimento original, não ordem alfabética).
    Variavel = apps.get_model("formularios", "Variavel")
    for variavel in Variavel.objects.all():
        opcoes = list(variavel.opcoes.all())
        if not opcoes:
            continue

        def chave_ordenacao(opcao):
            valor_normalizado = opcao.valor.strip().lower()
            eh_outro = valor_normalizado in ("outro", "outra")
            return (eh_outro, valor_normalizado)

        for indice, opcao in enumerate(sorted(opcoes, key=chave_ordenacao)):
            if opcao.ordem != indice:
                opcao.ordem = indice
                opcao.save(update_fields=["ordem"])


def reverter(apps, schema_editor):
    # Não dá pra recuperar a ordem original (era só ordem de import, nunca
    # guardada em outro lugar) — reversão não desfaz o reordenamento, só
    # existe pra a migração ser reversível estruturalmente.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('formularios', '0007_categoria_formulario'),
    ]

    operations = [
        migrations.RunPython(reordenar_opcoes_alfabetico, reverter),
    ]
