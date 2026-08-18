from django import forms

from accounts.models import Usuario
from core.form_utils import personalizar_opcoes_vazias
from projetos.models import Perfil

from .models import Participante, Profissao


class SelectProfissao(forms.Select):
    """`<select>` de profissão em que cada `<option>` carrega
    `data-especialidade="1"` quando aquela profissão tem especialidade — é
    isso que o JS (`static/js/profissao_especialidade.js`) lê pra decidir se
    mostra o campo de texto livre "Especialidade". Guarda o conjunto de PKs
    com especialidade numa única consulta (não uma por `<option>`)."""

    _pks_com_especialidade = None

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        pk = getattr(value, "value", value)
        if pk in (None, ""):
            return option
        if self._pks_com_especialidade is None:
            self._pks_com_especialidade = {
                str(pk) for pk in Profissao.objects.filter(tem_especialidade=True).values_list("pk", flat=True)
            }
        if str(pk) in self._pks_com_especialidade:
            option["attrs"]["data-especialidade"] = "1"
        return option


class ParticipanteForm(forms.ModelForm):
    consentimento_lgpd = forms.BooleanField(
        label="O participante aceitou o Termo de Consentimento LGPD vigente",
        required=True,
    )
    # UF vira lista fixa (só 27 opções, não muda) e Cidade vira uma lista
    # populada em JS (static/js/endereco_cep.js) a partir da API do IBGE,
    # conforme o estado escolhido — por isso o widget nasce com só um
    # placeholder; as opções de verdade chegam depois, no navegador.
    uf = forms.ChoiceField(choices=[("", "Selecione…"), *Participante.UF.choices], label="UF")
    cidade = forms.CharField(label="Cidade", widget=forms.Select())

    class Meta:
        model = Participante
        fields = [
            "nome",
            "cpf",
            "data_nascimento",
            "genero",
            "raca",
            "telefone",
            "email",
            "cep",
            "regiao",
            "uf",
            "cidade",
            "bairro",
            "escolaridade",
            "profissao",
            "especialidade",
            "ocupacao",
            "estado_civil",
            "renda_individual",
            "renda_familiar",
            "situacao",
            "forma_pagamento",
            "chave_pix",
            "consentimento_lgpd",
        ]
        widgets = {
            "data_nascimento": forms.DateInput(attrs={"type": "date"}),
            "profissao": SelectProfissao(),
            "especialidade": forms.TextInput(attrs={"placeholder": "Ex.: Cardiologista"}),
        }
        labels = {
            "nome": "Nome completo",
            "cpf": "CPF",
            "data_nascimento": "Data de nascimento",
            "genero": "Gênero",
            "raca": "Raça/cor",
            "telefone": "Telefone",
            "email": "E-mail",
            "cep": "CEP",
            "bairro": "Bairro",
            "regiao": "Região",
            "escolaridade": "Escolaridade",
            "profissao": "Profissão",
            "especialidade": "Especialidade",
            "ocupacao": "Ocupação",
            "estado_civil": "Estado civil",
            "renda_individual": "Renda individual",
            "renda_familiar": "Renda familiar",
            "situacao": "Situação",
            "forma_pagamento": "Forma de pagamento",
            "chave_pix": "Chave PIX",
        }

    def __init__(self, *args, pode_ver_pagamento=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["profissao"].empty_label = "Selecione…"
        if not pode_ver_pagamento:
            self.fields.pop("forma_pagamento")
            self.fields.pop("chave_pix")
        # Sem isso, editar um participante existente mostraria o campo Cidade
        # vazio (o `<select>` só ganha as opções de verdade via JS, depois
        # que o estado é escolhido) — injeta a cidade atual como a única
        # opção válida até o JS repopular a lista de verdade.
        cidade_atual = self.initial.get("cidade") or (self.instance.cidade if self.instance and self.instance.pk else "")
        if cidade_atual:
            self.fields["cidade"].widget.choices = [("", "Selecione…"), (cidade_atual, cidade_atual)]
        else:
            self.fields["cidade"].widget.choices = [("", "Selecione o estado primeiro")]
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
        # O formset manual do wizard tem N linhas de uma vez — não vale a pena
        # religar a busca de CEP/estado→cidade por JS em cada uma. Volta UF e
        # Cidade a serem texto livre, como sempre foram aqui (CSV também só
        # manda essas colunas como texto puro).
        self.fields["uf"] = forms.CharField(label="UF", max_length=2)
        self.fields["cidade"] = forms.CharField(label="Cidade")


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


class RenovarTermoForm(forms.Form):
    """Tela pública de renovação de termo/contrato (`pessoas:renovar_termo`)
    — confirma identidade pelo CPF (tem que bater com o cadastro pra aceitar
    o documento) e pede e-mail só como informação de contato, sem comparar
    com o que já está salvo: a mesma pessoa pode ter mais de um e-mail ao
    longo do tempo, então um e-mail diferente não deveria travar o aceite."""

    cpf = forms.CharField(label="CPF")
    email = forms.EmailField(label="E-mail")
    aceite = forms.BooleanField(label="Li o texto acima e aceito esta versão do documento.", required=True)


class EscolherProjetoWizardForm(forms.Form):
    # Perfis de projeto concluído continuam na lista de propósito — é
    # exatamente o caso de uso de um lote legado (`legado` abaixo), que
    # quase sempre é de um projeto que já terminou há tempos.
    perfil = forms.ModelChoiceField(
        queryset=Perfil.objects.select_related("projeto").order_by("projeto__nome", "nome"),
        required=False,
        empty_label="Apenas para o Banco de Pessoas (sem perfil)",
        label="Associar os novos participantes a um perfil?",
    )
    recrutador = forms.ModelChoiceField(
        queryset=Usuario.objects.filter(is_active=True).order_by("first_name", "username"),
        required=False,
        empty_label="Eu mesmo(a) — quem está enviando este lote",
        label="Recrutador responsável por este lote",
        help_text="Fica registrado como quem indicou os participantes criados neste lote.",
    )
    legado = forms.BooleanField(
        required=False,
        label="Este lote é de um projeto legado (já concluído) — só preencher o Banco de Pessoas",
        help_text=(
            "Aceita os dados da planilha como vierem, sem exigir campos obrigatórios "
            "completos nem bloquear por formato — só confere que não é a mesma pessoa já "
            "cadastrada. Cadastros com dado faltando ficam marcados pra atualizar depois."
        ),
    )


class UploadCSVForm(forms.Form):
    arquivo = forms.FileField(label="Planilha (.xlsx ou .csv)")

    def clean_arquivo(self):
        arquivo = self.cleaned_data["arquivo"]
        nome = (arquivo.name or "").lower()
        if not nome.endswith((".xlsx", ".csv")):
            raise forms.ValidationError("Envie um arquivo .xlsx ou .csv.")
        return arquivo
