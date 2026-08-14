from django import forms
from django.forms import formset_factory

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
    class Meta:
        model = Perfil
        fields = ["nome"]
        labels = {"nome": "Nome do perfil"}


class FormularioSelecaoForm(forms.Form):
    """Uma linha por formulário ativo disponível — `incluir` decide se ele
    entra no perfil, `ordem` decide a posição. Mesmo padrão de
    `formularios/forms.py::VariavelSelecaoForm` (lá é formulário↔variável,
    aqui é perfil↔formulário)."""

    formulario_id = forms.UUIDField(widget=forms.HiddenInput)
    incluir = forms.BooleanField(required=False)
    ordem = forms.IntegerField(required=False, min_value=0, initial=0)


FormularioSelecaoFormSet = formset_factory(FormularioSelecaoForm, extra=0)


def montar_formset_formularios_perfil(perfil=None, data=None):
    """Devolve (linhas, formset) — `linhas` é uma lista de (Formulario,
    subformulário) na mesma ordem, pronta pra iterar num único `{% for %}`
    no template. Mesma estrutura de
    `formularios/forms.py::montar_formset_variaveis`."""
    formularios_ativos = Formulario.objects.filter(ativo=True).order_by("nome")
    associados = {}
    if perfil is not None and perfil.pk:
        associados = {pf.formulario_id: pf.ordem for pf in perfil.perfil_formularios.all()}
    initial = [
        {
            "formulario_id": f.pk,
            "incluir": f.pk in associados,
            "ordem": associados.get(f.pk, indice),
        }
        for indice, f in enumerate(formularios_ativos)
    ]
    formset = FormularioSelecaoFormSet(data, initial=initial, prefix="forms_perfil")
    linhas = list(zip(formularios_ativos, formset.forms))
    return linhas, formset
