from django.contrib import admin

from .models import Projeto


@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ("nome", "cliente", "status", "vagas", "criado_em")
    list_filter = ("status",)
    search_fields = ("nome", "cliente")
