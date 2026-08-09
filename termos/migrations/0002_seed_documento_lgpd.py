import datetime

from django.db import migrations

TEXTO_LGPD = """TERMO DE CONSENTIMENTO PARA TRATAMENTO DE DADOS PESSOAIS (LGPD)

1. Finalidade: seus dados pessoais (nome, CPF, contato, perfil socioeconômico) serão
utilizados exclusivamente para fins de recrutamento e participação em pesquisas de mercado
conduzidas pela Qualy Vortice e por seus clientes contratantes.

2. Compartilhamento: dados podem ser compartilhados com o cliente contratante do projeto
específico para o qual você foi selecionado(a), sempre limitados ao necessário para a
condução da pesquisa.

3. Retenção: seus dados serão mantidos pelo prazo de 5 (cinco) anos após a última
participação, podendo ser anonimizados ou eliminados a seu pedido, respeitadas as obrigações
legais de guarda de registros.

4. Direitos do titular: você pode solicitar a qualquer momento acesso, correção ou exclusão
dos seus dados, através do canal de atendimento do Encarregado de Dados (DPO).

5. Base legal: o tratamento é realizado com fundamento no seu consentimento livre,
informado e inequívoco, nos termos do art. 7º, I, da Lei nº 13.709/2018 (LGPD).

Ao aceitar este termo, você declara estar ciente e de acordo com as condições acima."""


def seed(apps, schema_editor):
    Termo = apps.get_model("termos", "Termo")
    VersaoTermo = apps.get_model("termos", "VersaoTermo")
    LogAlteracao = apps.get_model("termos", "LogAlteracao")

    termo, _ = Termo.objects.get_or_create(
        nome="Termo de Consentimento LGPD",
        defaults={"tipo": "CONSENTIMENTO"},
    )
    if not termo.versoes.exists():
        versao = VersaoTermo.objects.create(
            termo=termo,
            versao=f"v{datetime.date.today().year}.1",
            texto=TEXTO_LGPD,
            inicio_vigencia=datetime.date.today(),
            status="VIGENTE",
        )
        LogAlteracao.objects.create(
            versao=versao, acao=f"Documento criado com a versão {versao.versao}"
        )


def remover(apps, schema_editor):
    Termo = apps.get_model("termos", "Termo")
    Termo.objects.filter(nome="Termo de Consentimento LGPD").delete()


class Migration(migrations.Migration):
    dependencies = [("termos", "0001_initial")]

    operations = [migrations.RunPython(seed, remover)]
