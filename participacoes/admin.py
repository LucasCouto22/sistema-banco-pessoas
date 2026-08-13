from django.contrib import admin

from .models import Avaliacao, Participacao


@admin.register(Participacao)
class ParticipacaoAdmin(admin.ModelAdmin):
    list_display = ("participante", "perfil", "etapa", "status", "responsavel")
    list_filter = ("etapa", "status")


@admin.register(Avaliacao)
class AvaliacaoAdmin(admin.ModelAdmin):
    list_display = ("participacao", "nota_geral", "avaliado_por", "avaliado_em")
