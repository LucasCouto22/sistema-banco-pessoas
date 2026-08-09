from django import forms

from core.form_utils import personalizar_opcoes_vazias

from .models import Projeto


class ProjetoForm(forms.ModelForm):
    class Meta:
        model = Projeto
        fields = [
            "nome",
            "cliente",
            "metodologia",
            "status",
            "segmento",
            "data_inicio",
            "data_fim",
            "incentivo",
            "valor_perfil",
            "vagas",
            "descricao",
            "perfil_idade_min",
            "perfil_idade_max",
            "perfil_genero",
            "perfil_regiao",
            "perfil_renda",
            "perfil_criterios_livres",
        ]
        widgets = {
            "data_inicio": forms.DateInput(attrs={"type": "date"}),
            "data_fim": forms.DateInput(attrs={"type": "date"}),
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "perfil_criterios_livres": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "nome": "Nome do projeto",
            "cliente": "Cliente",
            "metodologia": "Metodologia",
            "status": "Status",
            "segmento": "Segmento",
            "data_inicio": "Início do campo",
            "data_fim": "Fim do campo",
            "incentivo": "Incentivo (R$)",
            "valor_perfil": "Valor por perfil (R$)",
            "vagas": "Vagas",
            "descricao": "Descrição / briefing",
            "perfil_idade_min": "Idade mínima",
            "perfil_idade_max": "Idade máxima",
            "perfil_genero": "Gênero desejado",
            "perfil_regiao": "Região",
            "perfil_renda": "Faixa de renda desejada",
            "perfil_criterios_livres": "Outros critérios",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        personalizar_opcoes_vazias(self)
