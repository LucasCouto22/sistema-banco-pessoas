"""E-mails transacionais do app `accounts` — hoje só o aviso de conta nova
(disparado em `views.py::usuario_novo`). Redefinição de senha usa o
mecanismo de e-mail do próprio `PasswordResetForm`/`PasswordResetView` do
Django (`accounts/views.py`), não passa por aqui."""

import logging

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def enviar_email_novo_usuario(usuario, request):
    """Avisa o usuário recém-criado por e-mail — best effort: se o envio
    falhar (Mailgun fora do ar, domínio sandbox recusando destinatário não
    autorizado, etc.), só registra no log; não desfaz nem trava a criação
    do usuário, que já está salva no banco antes desta função ser chamada.
    Devolve `True`/`False` conforme o envio deu certo, pra quem chamou poder
    avisar o admin na tela se precisar."""
    contexto = {
        "usuario": usuario,
        "protocol": "https" if request.is_secure() else "http",
        "domain": request.get_host(),
    }
    assunto = render_to_string("accounts/email/usuario_criado_assunto.txt", contexto).strip()
    corpo_texto = render_to_string("accounts/email/usuario_criado.txt", contexto)
    corpo_html = render_to_string("accounts/email/usuario_criado.html", contexto)

    email = EmailMultiAlternatives(assunto, corpo_texto, to=[usuario.email])
    email.attach_alternative(corpo_html, "text/html")
    try:
        email.send(fail_silently=False)
        return True
    except Exception:
        logger.exception("Falha ao mandar e-mail de conta criada pra %s", usuario.email)
        return False
