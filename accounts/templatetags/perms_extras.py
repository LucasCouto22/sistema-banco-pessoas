from django import template

register = template.Library()


@register.filter
def tem_permissao(user, codigo):
    return user.is_authenticated and user.tem_permissao(codigo)


@register.filter
def nome_usuario(usuario):
    """Nome de exibição de um usuário que pode ser None (ex.: FK nula em dado semeado)."""
    if not usuario:
        return "—"
    return usuario.get_full_name() or usuario.username
