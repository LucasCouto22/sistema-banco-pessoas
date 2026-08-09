from django import forms


def personalizar_opcoes_vazias(form, texto="Selecione…"):
    """Troca o rótulo padrão da opção em branco dos <select> vindos de choices
    de modelo (Django usa "---------"; o navegador pode preencher um texto em
    inglês quando a opção está vazia) por um texto em português."""
    for field in form.fields.values():
        if isinstance(field, forms.ModelChoiceField):
            continue
        if not isinstance(field, forms.ChoiceField):
            continue
        choices = list(field.choices)
        if choices and choices[0][0] == "":
            choices[0] = ("", texto)
            field.choices = choices
