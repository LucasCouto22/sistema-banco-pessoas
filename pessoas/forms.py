from django import forms

from core.form_utils import personalizar_opcoes_vazias
from projetos.models import Projeto

from .models import Participante


class ParticipanteForm(forms.ModelForm):
    consentimento_lgpd = forms.BooleanField(
        label="O participante aceitou o Termo de Consentimento LGPD vigente",
        required=True,
    )

    class Meta:
        model = Participante
        fields = [
            "nome",
            "cpf",
            "data_nascimento",
            "genero",
            "telefone",
            "email",
            "cidade",
            "uf",
            "cep",
            "escolaridade",
            "profissao",
            "faixa_renda",
            "situacao",
            "forma_pagamento",
            "chave_pix",
            "consentimento_lgpd",
        ]
        widgets = {
            "data_nascimento": forms.DateInput(attrs={"type": "date"}),
        }
        labels = {
            "nome": "Nome completo",
            "cpf": "CPF",
            "data_nascimento": "Data de nascimento",
            "genero": "Gênero",
            "telefone": "Telefone",
            "email": "E-mail",
            "cidade": "Cidade",
            "uf": "UF",
            "cep": "CEP",
            "escolaridade": "Escolaridade",
            "profissao": "Profissão",
            "faixa_renda": "Faixa de renda",
            "situacao": "Situação",
            "forma_pagamento": "Forma de pagamento",
            "chave_pix": "Chave PIX",
        }

    def __init__(self, *args, pode_ver_pagamento=True, **kwargs):
        super().__init__(*args, **kwargs)
        if not pode_ver_pagamento:
            self.fields.pop("forma_pagamento")
            self.fields.pop("chave_pix")
        personalizar_opcoes_vazias(self)


class ParticipanteWizardForm(ParticipanteForm):
    """Mesma validação do cadastro individual, mas sem os campos de consentimento e
    situação — no wizard de importação em massa o consentimento é confirmado linha a
    linha na etapa de revisão (não no formulário de dados) e toda linha nova entra
    como "Pendente" (definido no servidor). Isso também é necessário para o formset
    manual: um ChoiceField com valor padrão sempre preenchido impediria o Django de
    reconhecer uma linha em branco como opcional (todas pareceriam "preenchidas")."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("pode_ver_pagamento", False)
        super().__init__(*args, **kwargs)
        self.fields.pop("situacao", None)
        self.fields.pop("consentimento_lgpd", None)


def participante_wizard_formset(extra=0):
    return forms.formset_factory(ParticipanteWizardForm, extra=extra)


class CadastroPublicoForm(ParticipanteForm):
    """Formulário da página pública de cadastro (sem login). Mantém o campo de
    consentimento — aqui é a própria pessoa quem aceita o termo, diferente do wizard
    interno, onde o consentimento é confirmado pelo operador na revisão."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("pode_ver_pagamento", False)
        super().__init__(*args, **kwargs)
        self.fields.pop("situacao", None)


class EscolherProjetoWizardForm(forms.Form):
    projeto = forms.ModelChoiceField(
        queryset=Projeto.objects.exclude(status=Projeto.Status.CONCLUIDO),
        required=False,
        empty_label="Apenas para o Banco de Pessoas (sem projeto)",
        label="Associar os novos participantes a um projeto?",
    )


class UploadCSVForm(forms.Form):
    arquivo = forms.FileField(label="Planilha (.csv)")
