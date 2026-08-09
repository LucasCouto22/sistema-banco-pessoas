from django.contrib import admin

from .models import RegistroAcesso


@admin.register(RegistroAcesso)
class RegistroAcessoAdmin(admin.ModelAdmin):
    list_display = ("quando", "usuario", "titular", "acao", "detalhe")
    list_filter = ("acao",)
    search_fields = ("titular", "detalhe")
    readonly_fields = ("quando", "usuario", "titular", "acao", "detalhe")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
