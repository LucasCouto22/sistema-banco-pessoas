/* Botão "+ Adicionar opção" do formset de Opções de resposta — clona o
   `<template>` do formset (`formset.empty_form`, com "__prefix__" no lugar
   do índice) e troca "__prefix__" pelo próximo índice livre, incrementando
   o TOTAL_FORMS do management form. Padrão padrão de formset dinâmico do
   Django (não tem suporte nativo em JS, então é sempre feito assim). */
(function () {
  "use strict";

  var lista = document.getElementById("opcoes-lista");
  var template = document.getElementById("opcao-form-template");
  var botaoAdicionar = document.getElementById("btn-add-opcao");
  var totalForms = document.getElementById("id_opcoes-TOTAL_FORMS");
  if (!lista || !template || !botaoAdicionar || !totalForms) return;

  botaoAdicionar.addEventListener("click", function () {
    var indice = parseInt(totalForms.value, 10);
    var html = template.innerHTML.split("__prefix__").join(String(indice));
    var wrapper = document.createElement("div");
    wrapper.innerHTML = html.trim();
    lista.appendChild(wrapper.firstElementChild);
    totalForms.value = String(indice + 1);
  });
})();
