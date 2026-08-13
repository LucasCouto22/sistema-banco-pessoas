from django.db import migrations

# Lista curta e curada (não é a CBO inteira, que tem mais de 2.600 ocupações
# bem granulares — inviável num dropdown simples). `tem_especialidade=True`
# é pra profissão em que costuma fazer sentido perguntar a área de atuação
# (ex.: Médico → Cardiologista, Professor → disciplina, Advogado → área do
# direito) — controla se o formulário abre o campo de texto livre
# "Especialidade" quando essa profissão é escolhida.
PROFISSOES = [
    # Saúde
    ("Médico(a)", True),
    ("Enfermeiro(a)", True),
    ("Dentista", True),
    ("Fisioterapeuta", True),
    ("Nutricionista", True),
    ("Psicólogo(a)", True),
    ("Farmacêutico(a)", True),
    ("Veterinário(a)", True),
    ("Fonoaudiólogo(a)", True),
    ("Biomédico(a)", True),
    ("Técnico(a) de Enfermagem", False),
    ("Terapeuta Ocupacional", False),
    ("Educador(a) Físico / Personal Trainer", True),
    # Educação
    ("Professor(a)", True),
    ("Pedagogo(a)", False),
    ("Coordenador(a) Pedagógico(a)", False),
    # Tecnologia
    ("Analista de Sistemas / TI", True),
    ("Desenvolvedor(a) de Software", True),
    ("Analista de Suporte Técnico", False),
    ("Analista de Dados", False),
    ("Designer", True),
    ("Analista de Redes", False),
    # Direito
    ("Advogado(a)", True),
    ("Assistente Jurídico(a)", False),
    # Engenharia e construção
    ("Engenheiro(a)", True),
    ("Arquiteto(a)", True),
    ("Técnico(a) em Edificações", False),
    ("Eletricista", False),
    ("Encanador(a)", False),
    ("Pedreiro(a)", False),
    ("Pintor(a)", False),
    ("Marceneiro(a)", False),
    ("Soldador(a)", False),
    # Administração e negócios
    ("Administrador(a)", False),
    ("Contador(a)", False),
    ("Analista Financeiro(a)", False),
    ("Analista de Recursos Humanos", False),
    ("Assistente Administrativo(a)", False),
    ("Gerente Comercial", False),
    ("Corretor(a) de Imóveis", False),
    ("Corretor(a) de Seguros", False),
    ("Consultor(a)", True),
    # Comunicação, design e mídia
    ("Jornalista", False),
    ("Publicitário(a)", False),
    ("Fotógrafo(a)", False),
    ("Redator(a)", False),
    ("Social Media", False),
    # Vendas e atendimento
    ("Vendedor(a)", False),
    ("Atendente", False),
    ("Recepcionista", False),
    ("Representante Comercial", False),
    # Serviços gerais e ofícios
    ("Cozinheiro(a) / Chef de Cozinha", False),
    ("Confeiteiro(a)", False),
    ("Cabeleireiro(a)", False),
    ("Esteticista", False),
    ("Manicure / Pedicure", False),
    ("Motorista", False),
    ("Motoboy / Entregador(a)", False),
    ("Segurança", False),
    ("Zelador(a) / Porteiro(a)", False),
    ("Diarista / Auxiliar de Limpeza", False),
    ("Costureiro(a)", False),
    ("Mecânico(a)", False),
    # Outros
    ("Estudante", False),
    ("Autônomo(a)", False),
    ("Do lar", False),
    ("Aposentado(a)", False),
]


def seed(apps, schema_editor):
    Profissao = apps.get_model("pessoas", "Profissao")
    for nome, tem_especialidade in PROFISSOES:
        Profissao.objects.get_or_create(nome=nome, defaults={"tem_especialidade": tem_especialidade})


def remover(apps, schema_editor):
    Profissao = apps.get_model("pessoas", "Profissao")
    Profissao.objects.filter(nome__in=[nome for nome, _ in PROFISSOES]).delete()


class Migration(migrations.Migration):
    dependencies = [("pessoas", "0004_profissao_model")]

    operations = [migrations.RunPython(seed, remover)]
