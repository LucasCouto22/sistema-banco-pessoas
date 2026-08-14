from django.contrib import admin

from .models import Perfil, Projeto


@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ("nome", "cliente", "status", "vagas", "criado_em")
    list_filter = ("status",)
    search_fields = ("nome", "cliente")


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("nome", "projeto", "criado_em")
    list_filter = ("projeto",)
    search_fields = ("nome", "projeto__nome")
