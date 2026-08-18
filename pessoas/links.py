from django.core.signing import BadSignature, dumps, loads

TOKEN_SALT = "captacao-publica"
TOKEN_SALT_RENOVACAO_TERMO = "renovacao-termo"


def gerar_token_captacao(perfil_id, recrutador_id):
    return dumps({"perfil_id": perfil_id, "recrutador_id": recrutador_id}, salt=TOKEN_SALT)


def ler_token_captacao(token):
    """Decodifica o token do link público. Levanta ValueError com mensagem amigável
    (em português, pra exibir direto na página) se o link for inválido.

    Não expira mais por tempo (sem `max_age`) — a validade do link agora depende só
    do status do projeto (`pessoas/views.py::cadastro_publico` só aceita cadastro
    enquanto o projeto está "Recrutando"), não de um prazo fixo de horas."""
    try:
        return loads(token, salt=TOKEN_SALT)
    except BadSignature as exc:
        raise ValueError("Este link de cadastro é inválido.") from exc


def gerar_token_renovacao_termo(participante_id, termo_id):
    """Token do link de renovação de termo/contrato (`pessoas:renovar_termo`)
    — identifica a pessoa e o documento, não uma versão específica: a
    versão mostrada é sempre a vigente *no momento em que o link é aberto*,
    então o mesmo link continua funcionando mesmo se o documento for
    atualizado de novo depois de gerado (mesma filosofia do link de
    cadastro público, que também não expira por tempo)."""
    return dumps({"participante_id": participante_id, "termo_id": termo_id}, salt=TOKEN_SALT_RENOVACAO_TERMO)


def ler_token_renovacao_termo(token):
    try:
        return loads(token, salt=TOKEN_SALT_RENOVACAO_TERMO)
    except BadSignature as exc:
        raise ValueError("Este link de renovação é inválido.") from exc
