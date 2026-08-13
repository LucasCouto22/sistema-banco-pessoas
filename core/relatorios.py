"""Utilidades compartilhadas pelos exportadores de PDF/XLSX do sistema — ponto
único que sabe onde fica a logo oficial, pra todo relatório novo reaproveitar
em vez de cada app resolver o caminho do arquivo por conta própria."""

from django.contrib.staticfiles import finders

CAMINHO_LOGO = "img/logo.png"


def caminho_logo():
    """Caminho absoluto da logo no disco, ou None se o arquivo ainda não foi
    adicionado — os relatórios devem continuar funcionando (só sem a imagem)
    nesse caso, em vez de quebrar."""
    return finders.find(CAMINHO_LOGO)
