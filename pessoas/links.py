from django.core.signing import BadSignature, dumps, loads

TOKEN_SALT = "captacao-publica"


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
