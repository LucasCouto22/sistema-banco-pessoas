from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Manda um e-mail de teste pelo backend configurado (Mailgun, via django-anymail) "
        "pra confirmar que o envio está funcionando de ponta a ponta. Em domínio sandbox do "
        "Mailgun, o destinatário precisa estar na lista de autorizados do painel do Mailgun "
        "(Sending → Domain settings → Authorized Recipients), senão o Mailgun recusa o envio."
    )

    def add_arguments(self, parser):
        parser.add_argument("destinatario", help="E-mail que vai receber o teste.")

    def handle(self, *args, **options):
        destinatario = options["destinatario"]
        if settings.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend":
            self.stdout.write(
                self.style.WARNING(
                    "MAILGUN_API_KEY não está definida — o e-mail vai só aparecer aqui no "
                    "terminal (backend de console), não vai ser enviado de verdade."
                )
            )
        enviados = send_mail(
            subject="Qualy Vortice — teste de envio de e-mail",
            message="Se você recebeu isso, o envio de e-mail via Mailgun está funcionando.",
            from_email=None,
            recipient_list=[destinatario],
        )
        if enviados:
            self.stdout.write(self.style.SUCCESS(f"E-mail de teste enviado pra {destinatario}."))
        else:
            raise CommandError("O backend de e-mail não confirmou o envio (0 mensagens enviadas).")
