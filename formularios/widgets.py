from django import forms


class DropdownCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    """Mesma coisa que `CheckboxSelectMultiple` (continua mandando um
    `<input type="checkbox">` por opção, então o POST não muda em nada) —
    só troca o template de renderização por um que agrupa as opções dentro
    de um dropdown fechado por padrão, com campo de busca quando há muitas
    opções. Criado porque perguntas com dezenas de opções (ex.: "quais
    marcas você usa", com 50+ marcas) ficavam com uma parede de checkboxes
    sempre visível — ver `static/js/dropdown_multiselect.js` pelo
    comportamento de abrir/fechar/buscar/contar selecionados."""

    template_name = "formularios/widgets/dropdown_checkbox_select.html"
