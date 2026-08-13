/* Mostra o bloco de "Opções de resposta" só quando o tipo de resposta
   selecionado exige uma lista fechada (select/radio/múltipla escolha) —
   os códigos que exigem opção vêm do servidor (core/formularios/models.py
   ::CODIGOS_COM_OPCOES), não hardcoded aqui, pra não desalinhar os dois. */
(function () {
  "use strict";

  var elMapa = document.getElementById("tipos-resposta-codigo");
  var select = document.getElementById("id_tipo_resposta");
  var bloco = document.getElementById("bloco-opcoes");
  if (!elMapa || !select || !bloco) return;

  var CODIGOS_COM_OPCOES = ["select", "radio", "multipla_escolha"];
  var mapa = JSON.parse(elMapa.textContent);

  function atualizar() {
    var codigo = mapa[select.value];
    bloco.style.display = CODIGOS_COM_OPCOES.indexOf(codigo) >= 0 ? "" : "none";
  }

  select.addEventListener("change", atualizar);
  atualizar();
})();
