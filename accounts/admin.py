from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import NivelPermissao, Permissao, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Nível de acesso", {"fields": ("nivel", "telefone")}),
    )
    list_display = ("username", "get_full_name", "email", "nivel", "is_active")
    list_filter = ("nivel", "is_active")


@admin.register(Permissao)
class PermissaoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "descricao", "grupo")
    list_filter = ("grupo",)


@admin.register(NivelPermissao)
class NivelPermissaoAdmin(admin.ModelAdmin):
    list_display = ("nivel", "permissao", "concedida")
    list_filter = ("nivel", "concedida")
