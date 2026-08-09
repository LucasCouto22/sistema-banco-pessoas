from django.contrib import admin

from .models import LogAlteracao, Termo, VersaoTermo


@admin.register(Termo)
class TermoAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "criado_em")
    list_filter = ("tipo",)


@admin.register(VersaoTermo)
class VersaoTermoAdmin(admin.ModelAdmin):
    list_display = ("termo", "versao", "status", "inicio_vigencia", "fim_vigencia", "publicado_em")
    list_filter = ("status",)


@admin.register(LogAlteracao)
class LogAlteracaoAdmin(admin.ModelAdmin):
    list_display = ("versao", "quando", "usuario", "acao")
