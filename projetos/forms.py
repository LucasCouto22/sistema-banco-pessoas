from django import forms

from core.form_utils import personalizar_opcoes_vazias
from formularios.models import Formulario

from .models import Perfil, Projeto


class ProjetoForm(forms.ModelForm):
    class Meta:
        model = Projeto
        fields = [
            "nome",
            "cliente",
            "marca",
            "metodologia",
            "status",
            "segmento",
            "data_inicio",
            "data_fim",
            "incentivo",
            "valor_perfil",
            "vagas",
            "descricao",
        ]
        widgets = {
            "data_inicio": forms.DateInput(attrs={"type": "date"}),
            "data_fim": forms.DateInput(attrs={"type": "date"}),
            "descricao": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "nome": "Nome do projeto",
            "cliente": "Cliente",
            "marca": "Marca",
            "metodologia": "Metodologia",
            "status": "Status",
            "segmento": "Segmento",
            "data_inicio": "Início do campo",
            "data_fim": "Fim do campo",
            "incentivo": "Incentivo (R$)",
            "valor_perfil": "Valor por perfil (R$)",
            "vagas": "Vagas",
            "descricao": "Descrição / briefing",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        personalizar_opcoes_vazias(self)


class PerfilForm(forms.ModelForm):
    formulario = forms.ModelChoiceField(
        queryset=Formulario.objects.filter(ativo=True).order_by("nome"),
        required=False,
        empty_label="Nenhum",
        label="Formulário",
    )

    class Meta:
        model = Perfil
        fields = ["nome", "formulario"]
        labels = {"nome": "Nome do perfil"}
