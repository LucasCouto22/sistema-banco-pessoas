from django.contrib import admin

from .models import Participante


@admin.register(Participante)
class ParticipanteAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nome", "cidade", "uf", "situacao", "criado_em")
    list_filter = ("situacao", "uf", "escolaridade")
    search_fields = ("codigo", "nome", "cpf", "email")
    readonly_fields = ("codigo", "criado_em", "atualizado_em")
