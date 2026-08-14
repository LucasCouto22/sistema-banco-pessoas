"""Upsert de Participante por CPF/e-mail/telefone — usado em todo fluxo de
cadastro (formulário interno, cadastro público, wizard de importação em
lote) pra, ao achar uma pessoa já cadastrada, atualizar o registro dela em
vez de rejeitar ou duplicar.

Prioridade de casamento: **CPF primeiro** — é o único dos três campos com
unicidade garantida no banco (`Participante.cpf` é `unique=True`); e-mail e
telefone não são únicos hoje, então só entram como reforço quando o CPF não
veio preenchido ou não bateu com ninguém. Isso evita fundir por engano duas
pessoas que só dividem um telefone de família, por exemplo — decisão
confirmada com o usuário."""

import re
from datetime import date

from django.db.models import Value
from django.db.models.functions import Replace

from .models import Participante
from .validators import normalizar_cpf

# Data usada quando um lote legado não traz data de nascimento — bem no
# passado de propósito, pra ficar óbvio num relatório/dashboard que é um
# valor de preenchimento, não uma data real (idade "126 anos" chama atenção
# em vez de passar despercebida como uma data plausível qualquer).
DATA_NASCIMENTO_NAO_INFORMADA = date(1900, 1, 1)

# Campos que o import de lote legado aceita vazios — pra cada um, o valor
# usado quando falta (`None` só pra CPF, que é `unique=True`; string vazia
# pros outros, que o CharField já aceita sem violar nada).
PLACEHOLDERS_LEGADO = {
    "cpf": None,
    "telefone": "",
    "uf": "",
    "cidade": "",
    "genero": "",
    "raca": "",
    "email": "",
    "bairro": "",
    "regiao": "",
    "escolaridade": "",
    "profissao": None,
    "ocupacao": "",
    "estado_civil": "",
    "renda_individual": "",
    "renda_familiar": "",
}

# Campos "de perfil" — atualizáveis por upsert. De propósito NÃO inclui:
# `codigo` (gerado, imutável), `situacao` (status de triagem — não é pra uma
# nova submissão reverter uma aprovação/descarte já feito), `consentimento_*`
# e `origem_recrutador` (têm efeito legal/de atribuição — cada fluxo que já
# lida com eles continua decidindo isso por conta própria, sem passar por
# aqui) e os campos de auditoria (`criado_por`, datas).
CAMPOS_ATUALIZAVEIS = [
    "nome",
    "cpf",
    "data_nascimento",
    "genero",
    "raca",
    "telefone",
    "email",
    "cep",
    "bairro",
    "uf",
    "cidade",
    "regiao",
    "escolaridade",
    "profissao",
    "especialidade",
    "ocupacao",
    "estado_civil",
    "renda_individual",
    "renda_familiar",
    "forma_pagamento",
    "chave_pix",
]


def normalizar_telefone(valor):
    return re.sub(r"\D", "", valor or "")


def _sem_pontuacao(campo):
    """Encadeia `Replace()` pra tirar a pontuação comum de telefone
    (`(`, `)`, espaço, `-`) direto na consulta, mesma técnica já usada aqui
    pra CPF (`Participante.objects.annotate(cpf_normalizado=...)`)."""
    expressao = campo
    for caractere in ("(", ")", " ", "-"):
        expressao = Replace(expressao, Value(caractere), Value(""))
    return expressao


def encontrar_participante_existente(cpf="", email="", telefone=""):
    """Acha um Participante já cadastrado que bate com os dados informados.
    Devolve `None` se nada bater com nenhuma das três chaves."""
    cpf_normalizado = normalizar_cpf(cpf)
    if cpf_normalizado:
        achado = (
            Participante.objects.annotate(
                cpf_normalizado=Replace(Replace("cpf", Value("."), Value("")), Value("-"), Value(""))
            )
            .filter(cpf_normalizado=cpf_normalizado)
            .first()
        )
        if achado:
            return achado

    email = (email or "").strip()
    if email:
        achado = Participante.objects.exclude(email="").filter(email__iexact=email).first()
        if achado:
            return achado

    telefone_normalizado = normalizar_telefone(telefone)
    if telefone_normalizado:
        achado = (
            Participante.objects.exclude(telefone="")
            .annotate(telefone_normalizado=_sem_pontuacao("telefone"))
            .filter(telefone_normalizado=telefone_normalizado)
            .first()
        )
        if achado:
            return achado

    return None


def capturar_valores_atuais(participante):
    """Tira uma "foto" dos campos atualizáveis antes de aplicar um formulário
    em cima do participante — usada por `restaurar_campos_vazios()` pra saber
    o que devolver quando a submissão nova vier com aquele campo vazio."""
    return {campo: getattr(participante, campo) for campo in CAMPOS_ATUALIZAVEIS}


def restaurar_campos_vazios(participante, cleaned_data, valores_originais):
    """Depois que um `ModelForm` (já validado) aplicou `cleaned_data` no
    `participante`, esta função devolve pro valor original qualquer campo
    atualizável que veio vazio na submissão — uma atualização incompleta não
    apaga dado que já existia, só preenche o que veio preenchido de fato."""
    for campo in CAMPOS_ATUALIZAVEIS:
        if campo not in cleaned_data:
            continue
        novo_valor = cleaned_data[campo]
        if novo_valor in (None, "", []):
            setattr(participante, campo, valores_originais[campo])


def preparar_linha_legado(dados):
    """Prepara uma linha de planilha de **lote legado** pra ser gravada sem
    passar pela validação normal do `ParticipanteWizardForm` — aceita os
    dados como vieram (CPF sem dígito verificador, telefone em qualquer
    formato, etc.), só recusando o que realmente não dá pra importar: nome
    em branco, ou nenhuma das três chaves de identidade (CPF/e-mail/
    telefone) presente — sem isso não dá nem pra checar se já é alguém
    cadastrado.

    Devolve `(dados_prontos, campos_incompletos, erro)`: `erro` != None
    significa que a linha foi recusada mesmo em modo legado; senão,
    `dados_prontos` já tem os placeholders aplicados nos campos
    obrigatórios que faltarem, e `campos_incompletos` é o conjunto de nomes
    de campo que levaram um placeholder (vazio = `set()` quando a linha já
    veio completa)."""
    dados = dict(dados)

    if not (dados.get("nome") or "").strip():
        return None, set(), "Nome em branco — não dá pra importar sem nome."

    tem_identidade = any((dados.get(campo) or "").strip() for campo in ("cpf", "email", "telefone"))
    if not tem_identidade:
        return None, set(), "Sem CPF, e-mail nem telefone — não dá pra conferir se já existe."

    campos_incompletos = set()

    data_nascimento_texto = (dados.get("data_nascimento") or "").strip()
    data_valida = None
    if data_nascimento_texto:
        try:
            data_valida = date.fromisoformat(data_nascimento_texto)
        except ValueError:
            data_valida = None
    if data_valida is None:
        dados["data_nascimento"] = DATA_NASCIMENTO_NAO_INFORMADA.isoformat()
        campos_incompletos.add("data_nascimento")
    else:
        dados["data_nascimento"] = data_valida.isoformat()

    for campo, placeholder in PLACEHOLDERS_LEGADO.items():
        if not (dados.get(campo) or "").strip():
            dados[campo] = placeholder
            campos_incompletos.add(campo)

    return dados, campos_incompletos, None


def aplicar_dados_legado(participante, dados, campos_incompletos, existente, valores_originais):
    """Copia `dados` (já passado por `preparar_linha_legado`) direto pro
    `participante`, sem ModelForm no meio — é o que permite gravar um
    cadastro incompleto (placeholder em campo obrigatório) sem cair na
    validação normal, que rejeitaria. Se `existente`, aplica a mesma regra
    de não apagar dado que já existia: qualquer campo que recebeu
    placeholder (inclusive `data_nascimento`, cujo placeholder não é uma
    string vazia como os outros) é tratado como "veio vazio" — não
    sobrescreve o valor real que a pessoa já tinha.

    Sempre atualiza `participante.cadastro_incompleto` (liga ou desliga,
    conforme o que faltou desta vez) — uma linha completa pode "curar" a
    flag de alguém que antes só tinha dado incompleto."""
    for campo in CAMPOS_ATUALIZAVEIS:
        if campo not in dados:
            continue
        valor = dados[campo]
        if campo == "profissao":
            participante.profissao_id = valor or None
        elif campo == "data_nascimento":
            if valor:
                participante.data_nascimento = date.fromisoformat(valor)
        else:
            setattr(participante, campo, valor)

    if existente:
        dados_para_restaurar = dict(dados)
        for campo in campos_incompletos:
            dados_para_restaurar[campo] = None
        restaurar_campos_vazios(participante, dados_para_restaurar, valores_originais)

    participante.cadastro_incompleto = bool(campos_incompletos)
