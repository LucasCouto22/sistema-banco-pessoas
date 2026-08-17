from django import forms
from django.forms import formset_factory, inlineformset_factory

from core.form_utils import personalizar_opcoes_vazias

from .models import CategoriaFormulario, Formulario, TipoResposta, Variavel, VariavelOpcao


class VariavelForm(forms.ModelForm):
    tipo_resposta = forms.ModelChoiceField(
        queryset=TipoResposta.objects.all(),
        empty_label="Selecione…",
        label="Tipo de resposta",
    )

    class Meta:
        model = Variavel
        fields = ["nome", "tipo_resposta", "obrigatoria", "ativa"]
        labels = {
            "nome": "Nome da variável",
            "obrigatoria": "Resposta obrigatória",
            "ativa": "Variável ativa",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance._state.adding:
            # UUID é gerado no Python (não pelo banco), então `instance.pk` já vem
            # preenchido mesmo antes de salvar — `_state.adding` é o jeito correto
            # de saber se ainda não existe linha no banco pra essa instância.
            self.fields.pop("ativa")
        personalizar_opcoes_vazias(self)


VariavelOpcaoFormSet = inlineformset_factory(
    Variavel,
    VariavelOpcao,
    fields=["valor"],
    extra=3,
    can_delete=True,
    widgets={"valor": forms.TextInput(attrs={"placeholder": "Ex.: Diária"})},
)


class FormularioForm(forms.ModelForm):
    categoria = forms.ModelChoiceField(
        queryset=CategoriaFormulario.objects.all(),
        required=False,
        empty_label="Sem categoria",
        label="Categoria",
    )

    class Meta:
        model = Formulario
        fields = ["nome", "descricao", "categoria", "inclui_campos_fixos", "ativo"]
        widgets = {"descricao": forms.Textarea(attrs={"rows": 3})}
        labels = {
            "nome": "Nome do formulário",
            "descricao": "Descrição",
            "inclui_campos_fixos": "Inclui os campos fixos do participante (nome, contato, etc.)",
            "ativo": "Formulário ativo",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance._state.adding:
            self.fields.pop("ativo")


class CategoriaFormularioForm(forms.ModelForm):
    class Meta:
        model = CategoriaFormulario
        fields = ["nome", "observacao"]
        widgets = {"observacao": forms.Textarea(attrs={"rows": 3})}
        labels = {"nome": "Nome da categoria", "observacao": "Observação"}


class VariavelSelecaoForm(forms.Form):
    """Uma linha por variável ativa disponível — `incluir` decide se ela entra no
    formulário, `ordem` decide a posição. A reordenação por arrastar-e-soltar fica
    pra uma etapa futura (é só polimento de UX); isso aqui já cobre o que o CRUD
    precisa: montar/alterar a lista com uma ordem explícita."""

    variavel_id = forms.UUIDField(widget=forms.HiddenInput)
    incluir = forms.BooleanField(required=False)
    ordem = forms.IntegerField(required=False, min_value=0, initial=0)


VariavelSelecaoFormSet = formset_factory(VariavelSelecaoForm, extra=0)


def montar_formset_variaveis(formulario=None, data=None):
    """Devolve (linhas, formset) — `linhas` é uma lista de (Variavel, subformulário)
    na mesma ordem, pronta pra iterar num único `{% for %}` no template."""
    variaveis_ativas = Variavel.objects.filter(ativa=True).order_by("nome")
    associadas = {}
    if formulario is not None and formulario.pk:
        associadas = {
            fv.variavel_id: fv.ordem for fv in formulario.formulario_variaveis.all()
        }
    initial = [
        {
            "variavel_id": v.pk,
            "incluir": v.pk in associadas,
            "ordem": associadas.get(v.pk, indice),
        }
        for indice, v in enumerate(variaveis_ativas)
    ]
    formset = VariavelSelecaoFormSet(data, initial=initial, prefix="vars")
    linhas = list(zip(variaveis_ativas, formset.forms))
    return linhas, formset


