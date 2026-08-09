from functools import wraps

from django.core.exceptions import PermissionDenied

# Catálogo de permissões do sistema: (codigo, descricao, grupo).
# Usado para popular a tabela Permissao via migração de dados e para
# renderizar o painel de permissões agrupado por área.
CATALOGO_PERMISSOES = [
    ("participantes.ver", "Ver a lista e o detalhe de participantes", "Banco de Pessoas"),
    ("participantes.gerenciar", "Criar e editar participantes", "Banco de Pessoas"),
    ("participantes.excluir", "Excluir participantes", "Banco de Pessoas"),
    ("participantes.revelar_pii", "Revelar CPF, telefone e e-mail sem máscara", "Banco de Pessoas"),
    ("projetos.ver", "Ver projetos e seus detalhes", "Projetos"),
    ("projetos.gerenciar", "Criar e editar projetos", "Projetos"),
    ("projetos.excluir", "Excluir projetos", "Projetos"),
    ("participacoes.ver", "Ver participações e o pipeline", "Participações"),
    ("participacoes.mover_etapa", "Mover participações entre etapas do funil", "Participações"),
    ("participacoes.excluir", "Remover participações do pipeline", "Participações"),
    ("avaliacao.criar", "Avaliar participações (notas e comentários)", "Participações"),
    ("pagamento.ver", "Ver dados de pagamento (forma e chave PIX)", "Financeiro"),
    ("termos.ver", "Ver termos, contratos e o histórico de versões", "Termos e Contratos"),
    ("termos.gerenciar", "Criar documentos e publicar novas versões (imutáveis)", "Termos e Contratos"),
    ("usuarios.gerenciar", "Criar e editar usuários do sistema", "Administração"),
    ("usuarios.excluir", "Excluir usuários do sistema", "Administração"),
    ("permissoes.gerenciar", "Editar a matriz de permissões por nível", "Administração"),
    ("auditoria.ver", "Ver o registro de auditoria LGPD", "Administração"),
    ("avisos.triagem_pendente", "Receber aviso de triagem de participantes pendente", "Avisos"),
    ("avisos.projetos_vagas", "Receber aviso de projetos com vagas e campo próximo", "Avisos"),
    ("avisos.termos_vencendo", "Receber aviso de termos vigentes perto de expirar", "Avisos"),
]


def requer_permissao(codigo):
    """Decorator de view que exige uma permissão específica do usuário logado."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated or not request.user.tem_permissao(codigo):
                raise PermissionDenied(f"Seu nível de acesso não tem a permissão '{codigo}'.")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
