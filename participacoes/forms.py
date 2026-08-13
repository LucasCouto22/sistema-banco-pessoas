from django import forms

from pessoas.models import Participante
from projetos.models import Perfil, Projeto

from .models import Avaliacao, Participacao


class ParticipacaoForm(forms.ModelForm):
    participante = forms.ModelChoiceField(
        queryset=Participante.objects.exclude(situacao=Participante.Situacao.DESCARTADO),
        label="Participante",
        empty_label="Selecione o participante",
    )
    perfil = forms.ModelChoiceField(
        queryset=Perfil.objects.select_related("projeto").exclude(projeto__status=Projeto.Status.CONCLUIDO),
        label="Perfil",
        empty_label="Selecione o perfil",
    )

    class Meta:
        model = Participacao
        fields = ["participante", "perfil", "etapa", "observacao"]
        widgets = {"observacao": forms.Textarea(attrs={"rows": 3})}
        labels = {"etapa": "Etapa inicial", "observacao": "Observação"}


# Ordem 5→1 (não 1→5) de propósito: o widget de estrelas usa
# `flex-direction:row-reverse` + seletor de irmãos em CSS pra pintar a
# estrela clicada e todas à esquerda dela sem precisar de JS — isso só
# funciona se o rádio de valor mais alto vier primeiro no HTML. Ver
# `static/css/base.css::.star-rating` e `templates/core/_campo_estrelas.html`.
NOTAS = [(n, str(n)) for n in range(5, 0, -1)]


class AvaliacaoForm(forms.ModelForm):
    comunicacao = forms.ChoiceField(choices=NOTAS, widget=forms.RadioSelect, label="Comunicação")
    pontualidade = forms.ChoiceField(choices=NOTAS, widget=forms.RadioSelect, label="Pontualidade")
    repertorio = forms.ChoiceField(choices=NOTAS, widget=forms.RadioSelect, label="Repertório")

    class Meta:
        model = Avaliacao
        fields = ["comunicacao", "pontualidade", "repertorio", "comentario"]
        widgets = {"comentario": forms.Textarea(attrs={"rows": 2})}
        labels = {"comentario": "Comentário"}
