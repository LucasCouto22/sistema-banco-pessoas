from django import forms

from pessoas.models import Participante
from projetos.models import Projeto

from .models import Avaliacao, Participacao


class ParticipacaoForm(forms.ModelForm):
    participante = forms.ModelChoiceField(
        queryset=Participante.objects.exclude(situacao=Participante.Situacao.DESCARTADO),
        label="Participante",
        empty_label="Selecione o participante",
    )
    projeto = forms.ModelChoiceField(
        queryset=Projeto.objects.exclude(status=Projeto.Status.CONCLUIDO),
        label="Projeto",
        empty_label="Selecione o projeto",
    )

    class Meta:
        model = Participacao
        fields = ["participante", "projeto", "etapa", "observacao"]
        widgets = {"observacao": forms.Textarea(attrs={"rows": 3})}
        labels = {"etapa": "Etapa inicial", "observacao": "Observação"}


NOTAS = [(n, str(n)) for n in range(1, 6)]


class AvaliacaoForm(forms.ModelForm):
    comunicacao = forms.ChoiceField(choices=NOTAS, widget=forms.RadioSelect, label="Comunicação")
    pontualidade = forms.ChoiceField(choices=NOTAS, widget=forms.RadioSelect, label="Pontualidade")
    repertorio = forms.ChoiceField(choices=NOTAS, widget=forms.RadioSelect, label="Repertório")
    nota_geral = forms.ChoiceField(choices=NOTAS, widget=forms.RadioSelect, label="Nota geral")

    class Meta:
        model = Avaliacao
        fields = ["comunicacao", "pontualidade", "repertorio", "nota_geral", "comentario"]
        widgets = {"comentario": forms.Textarea(attrs={"rows": 3})}
        labels = {"comentario": "Comentário"}
