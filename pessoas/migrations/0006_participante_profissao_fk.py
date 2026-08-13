import django.db.models.deletion
from django.db import migrations, models

# Troca o `profissao` de texto livre (CharField) pra uma FK em `Profissao`,
# em 4 passos na mesma migração — precisa ser assim (não dá pra fazer um
# `AlterField` direto de CharField pra ForeignKey) porque o Postgres exigiria
# converter o texto já existente ("Programador", "Eletricista"...) pra
# bigint, o que quebraria a migração:
#   1. adiciona o campo novo (`profissao_novo`, FK) ao lado do antigo;
#   2. RunPython casa o texto antigo com alguma `Profissao` já semeada (por
#      nome exato ou por um dicionário de apelidos comuns) e preenche o
#      campo novo — o que não achar correspondência fica sem profissão
#      (fica só no `especialidade`/textos soltos não migram, mas os dados
#      deste sistema são todos de teste, então essa perda é aceitável);
#   3. remove o campo antigo;
#   4. renomeia o novo pro nome final `profissao`.
APELIDOS = {
    "programador": "Desenvolvedor(a) de Software",
    "programadora": "Desenvolvedor(a) de Software",
    "eletricista": "Eletricista",
    "nutricionista": "Nutricionista",
    "professor": "Professor(a)",
    "professora": "Professor(a)",
    "vendedor": "Vendedor(a)",
    "vendedora": "Vendedor(a)",
    "designer": "Designer",
    "medico": "Médico(a)",
    "médico": "Médico(a)",
    "medica": "Médico(a)",
    "médica": "Médico(a)",
    "advogado": "Advogado(a)",
    "advogada": "Advogado(a)",
    "engenheiro": "Engenheiro(a)",
    "engenheira": "Engenheiro(a)",
    "dentista": "Dentista",
    "psicologo": "Psicólogo(a)",
    "psicóloga": "Psicólogo(a)",
    "enfermeiro": "Enfermeiro(a)",
    "enfermeira": "Enfermeiro(a)",
    "administrador": "Administrador(a)",
    "administradora": "Administrador(a)",
    "contador": "Contador(a)",
    "contadora": "Contador(a)",
    "motorista": "Motorista",
    "cabeleireiro": "Cabeleireiro(a)",
    "cabeleireira": "Cabeleireiro(a)",
    "estudante": "Estudante",
    "autonomo": "Autônomo(a)",
    "autônomo": "Autônomo(a)",
    "autonoma": "Autônomo(a)",
    "autônoma": "Autônomo(a)",
    "aposentado": "Aposentado(a)",
    "aposentada": "Aposentado(a)",
    "do lar": "Do lar",
    "arquiteto": "Arquiteto(a)",
    "arquiteta": "Arquiteto(a)",
    "veterinario": "Veterinário(a)",
    "veterinária": "Veterinário(a)",
    "jornalista": "Jornalista",
    "mecanico": "Mecânico(a)",
    "mecânico": "Mecânico(a)",
    "pedreiro": "Pedreiro(a)",
}


def migrar_dados(apps, schema_editor):
    Participante = apps.get_model("pessoas", "Participante")
    Profissao = apps.get_model("pessoas", "Profissao")
    profissoes_por_nome = {p.nome.lower(): p for p in Profissao.objects.all()}

    for participante in Participante.objects.exclude(profissao=""):
        texto = (participante.profissao or "").strip().lower()
        if not texto:
            continue
        chave = APELIDOS.get(texto, texto)
        profissao = profissoes_por_nome.get(chave.lower())
        if profissao:
            participante.profissao_novo = profissao
            participante.save(update_fields=["profissao_novo"])


def reverter_dados(apps, schema_editor):
    Participante = apps.get_model("pessoas", "Participante")
    Participante.objects.update(profissao_novo=None)


class Migration(migrations.Migration):
    dependencies = [("pessoas", "0005_seed_profissoes")]

    operations = [
        migrations.AddField(
            model_name="participante",
            name="profissao_novo",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="participantes",
                to="pessoas.profissao",
            ),
        ),
        migrations.RunPython(migrar_dados, reverter_dados),
        migrations.RemoveField(model_name="participante", name="profissao"),
        migrations.RenameField(model_name="participante", old_name="profissao_novo", new_name="profissao"),
    ]
