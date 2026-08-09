from django.core.signing import BadSignature, SignatureExpired, dumps, loads

TOKEN_SALT = "captacao-publica"
TOKEN_MAX_AGE = 60 * 60 * 48  # 48 horas


def gerar_token_captacao(projeto_id, recrutador_id):
    return dumps({"projeto_id": projeto_id, "recrutador_id": recrutador_id}, salt=TOKEN_SALT)


def ler_token_captacao(token):
    """Decodifica o token do link público. Levanta ValueError com mensagem amigável
    (em português, para exibir direto na página) se o link for inválido ou tiver
    passado das 48h de validade."""
    try:
        return loads(token, salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE)
    except SignatureExpired as exc:
        raise ValueError("Este link de cadastro expirou (validade de 48 horas).") from exc
    except BadSignature as exc:
        raise ValueError("Este link de cadastro é inválido.") from exc
