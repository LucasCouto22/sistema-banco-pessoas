import os

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def static_v(caminho):
    """Igual a `{% static %}`, mas gruda `?v=<data de modificação do arquivo>`
    na URL. Sem isso, o navegador guarda o CSS/JS em cache pela URL — que não
    muda entre uma edição e outra em desenvolvimento — e continua mostrando a
    versão antiga até um hard refresh manual (foi exatamente o que confundiu
    o usuário com o CSS do modal de avaliação: o arquivo no servidor já
    estava certo, só o navegador é que insistia no antigo).

    Em produção (`collectstatic` com `ManifestStaticFilesStorage`) o nome do
    arquivo já muda sozinho quando o conteúdo muda, então isso aqui não findar
    o arquivo original (comprimido/versionado) — nesse caso só devolve a URL
    normal, sem duplicar cache-busting."""
    url = static(caminho)
    caminho_absoluto = finders.find(caminho)
    if not caminho_absoluto:
        return url
    versao = int(os.path.getmtime(caminho_absoluto))
    separador = "&" if "?" in url else "?"
    return f"{url}{separador}v={versao}"
