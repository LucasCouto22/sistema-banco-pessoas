from django import template

register = template.Library()


@register.filter
def sem_pagina(get_params):
    """Reencoda um QueryDict (normalmente `request.GET`) tirando a chave
    `page` — usado pra montar os links de paginação e de exportação sem
    arrastar a página atual pra outro contexto (ex.: um link de exportação
    não deve herdar `page=3` de quem clicou nele estando na 3ª página)."""
    params = get_params.copy()
    params.pop("page", None)
    return params.urlencode()
