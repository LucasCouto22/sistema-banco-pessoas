from datetime import timedelta

from django.utils import timezone

from accounts.models import AvisoDispensado, PreferenciaAvisos
from pessoas.models import Participante
from projetos.models import Projeto
from termos.models import VersaoTermo

PRAZO_PROJETO_DIAS = 14
PRAZO_TERMO_DIAS = 30
MAX_ALERTAS = 5


def _categoria(chave):
    return chave.split(":", 1)[0]


def alertas(request):
    """Alertas reais mostrados na sidebar. Cada categoria só aparece para quem
    tem a permissão `avisos.<categoria>` (painel de permissões, por nível) *e*
    não desligou aquela categoria em "Meu perfil" (por usuário). Um aviso
    dispensado (botão ×) some até o conteúdo mudar — comparamos chave+texto,
    então se a contagem/prazo mudar ele volta a aparecer naturalmente."""
    usuario = getattr(request, "user", None)
    if not usuario or not usuario.is_authenticated:
        return {}

    candidatos = []
    hoje = timezone.localdate()

    if usuario.tem_permissao("avisos.triagem_pendente"):
        pendentes = Participante.objects.filter(situacao=Participante.Situacao.PENDENTE).count()
        if pendentes:
            candidatos.append(
                {
                    "chave": "triagem_pendente",
                    "titulo": "Triagem pendente",
                    "detalhe": f"{pendentes} participante(s) aguardando aprovação ou descarte.",
                }
            )

    if usuario.tem_permissao("avisos.projetos_vagas"):
        limite = hoje + timedelta(days=PRAZO_PROJETO_DIAS)
        projetos = Projeto.objects.exclude(status=Projeto.Status.CONCLUIDO).filter(
            data_inicio__isnull=False, data_inicio__gte=hoje, data_inicio__lte=limite
        )
        for projeto in projetos:
            faltam = projeto.vagas - projeto.ocupadas
            if faltam > 0:
                dias = (projeto.data_inicio - hoje).days
                candidatos.append(
                    {
                        "chave": f"projetos_vagas:{projeto.pk}",
                        "titulo": projeto.nome,
                        "detalhe": f"Faltam {faltam} vaga(s) e o campo começa em {dias} dia(s).",
                    }
                )

    if usuario.tem_permissao("avisos.termos_vencendo"):
        limite = hoje + timedelta(days=PRAZO_TERMO_DIAS)
        expirando = VersaoTermo.objects.filter(
            status="VIGENTE", fim_vigencia__isnull=False, fim_vigencia__gte=hoje, fim_vigencia__lte=limite
        ).count()
        if expirando:
            candidatos.append(
                {
                    "chave": "termos_vencendo",
                    "titulo": "Consentimentos",
                    "detalhe": f"{expirando} termo(s) vigente(s) perto de expirar (30 dias).",
                }
            )

    if not candidatos:
        return {"alertas_sidebar": [], "total_alertas_sidebar": 0}

    preferencia = PreferenciaAvisos.para(usuario)
    mapa_preferencia = {
        "triagem_pendente": preferencia.triagem_pendente,
        "projetos_vagas": preferencia.projetos_vagas,
        "termos_vencendo": preferencia.termos_vencendo,
    }
    candidatos = [c for c in candidatos if mapa_preferencia.get(_categoria(c["chave"]), True)]

    if candidatos:
        dispensados = set(
            AvisoDispensado.objects.filter(usuario=usuario).values_list("chave", "conteudo")
        )
        candidatos = [c for c in candidatos if (c["chave"], c["detalhe"]) not in dispensados]

    return {"alertas_sidebar": candidatos[:MAX_ALERTAS], "total_alertas_sidebar": len(candidatos)}
