from django import forms

from core.form_utils import personalizar_opcoes_vazias

from .models import Termo, VersaoTermo


class TermoForm(forms.ModelForm):
    versao = forms.CharField(
        max_length=20,
        required=False,
        label="Versão",
        help_text="Deixe em branco para gerar automaticamente (ex.: v2026.1).",
    )
    texto = forms.CharField(label="Texto do documento", widget=forms.Textarea(attrs={"rows": 10}))
    inicio_vigencia = forms.DateField(label="Início de vigência", widget=forms.DateInput(attrs={"type": "date"}))
    fim_vigencia = forms.DateField(
        label="Fim de vigência", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )

    class Meta:
        model = Termo
        fields = ["nome", "tipo"]
        labels = {"nome": "Nome do documento", "tipo": "Tipo"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        personalizar_opcoes_vazias(self)


class VersaoTermoForm(forms.ModelForm):
    class Meta:
        model = VersaoTermo
        fields = ["inicio_vigencia", "fim_vigencia", "texto"]
        widgets = {
            "inicio_vigencia": forms.DateInput(attrs={"type": "date"}),
            "fim_vigencia": forms.DateInput(attrs={"type": "date"}),
            "texto": forms.Textarea(attrs={"rows": 10}),
        }
        labels = {
            "inicio_vigencia": "Início de vigência",
            "fim_vigencia": "Fim de vigência",
            "texto": "Texto do documento",
        }
