from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Garante que o schema 'pessoas' existe no Postgres antes de rodar as migrações."

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("CREATE SCHEMA IF NOT EXISTS pessoas;")
        self.stdout.write(self.style.SUCCESS("Schema 'pessoas' garantido no banco."))
