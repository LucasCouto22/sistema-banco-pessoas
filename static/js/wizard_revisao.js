(function () {
  "use strict";

  // Botão "Editar"/"Fechar" de cada linha — alterna a classe que abre/fecha
  // a linha de edição (CSS cuida do display, inclusive no card do mobile).
  document.addEventListener("click", function (evento) {
    var botao = evento.target.closest("[data-toggle-linha]");
    if (!botao) return;
    var linha = document.getElementById(botao.getAttribute("data-toggle-linha"));
    if (!linha) return;
    var abriu = linha.classList.toggle("wiz-aberta");
    botao.textContent = abriu ? "Fechar" : "Editar";
  });

  // Checkbox no cabeçalho da coluna "Consentimento LGPD" — marca/desmarca
  // todas as caixas da coluna de uma vez.
  var marcarTodos = document.getElementById("wizConsentimentoTodos");
  if (!marcarTodos) return;
  var caixas = document.querySelectorAll('input[name^="consentimento_"]');
  marcarTodos.addEventListener("change", function () {
    caixas.forEach(function (caixa) { caixa.checked = marcarTodos.checked; });
  });
  // Se alguém desmarcar uma caixa individual, o "marcar todos" deixa de
  // representar "tudo marcado" — evita o cabeçalho mentir sobre o estado.
  caixas.forEach(function (caixa) {
    caixa.addEventListener("change", function () {
      if (!caixa.checked) marcarTodos.checked = false;
    });
  });
})();
