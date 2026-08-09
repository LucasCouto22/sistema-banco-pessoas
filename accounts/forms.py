from django import forms
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm

from core.form_utils import personalizar_opcoes_vazias

from .models import PreferenciaAvisos, Usuario

LABELS_USUARIO = {
    "username": "Usuário",
    "first_name": "Nome",
    "last_name": "Sobrenome",
    "email": "E-mail",
    "nivel": "Nível de acesso",
    "telefone": "Telefone",
}


class UsuarioCreateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("username", "first_name", "last_name", "email", "nivel", "telefone")
        labels = LABELS_USUARIO

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].label = "Senha provisória"
        self.fields["password2"].label = "Confirme a senha"
        personalizar_opcoes_vazias(self)


class UsuarioEditForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ("first_name", "last_name", "email", "nivel", "telefone", "is_active")
        labels = {**LABELS_USUARIO, "is_active": "Usuário ativo"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        personalizar_opcoes_vazias(self)


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ("first_name", "last_name", "email", "telefone")
        labels = LABELS_USUARIO


class PreferenciaAvisosForm(forms.ModelForm):
    class Meta:
        model = PreferenciaAvisos
        fields = ("triagem_pendente", "projetos_vagas", "termos_vencendo")


class TrocarSenhaForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].label = "Senha atual"
        self.fields["new_password1"].label = "Nova senha"
        self.fields["new_password2"].label = "Confirme a nova senha"
