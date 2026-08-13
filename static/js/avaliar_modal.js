/* Modal de avaliação usado em `templates/participacoes/lista.html` — um só
   modal na página, reaproveitado por todas as linhas da tabela: cada botão
   "Avaliar"/"Editar" carrega os dados daquela participação em atributos
   `data-*` (pk, nomes, notas já existentes) e este script usa isso pra
   apontar o formulário pra URL certa e pré-marcar as estrelas antes de
   abrir. Continua sendo um <form method="post"> de verdade — sem fetch,
   sem JSON — só a abertura/fechamento do modal é feita em JS. */
(function () {
  "use strict";

  var form = document.getElementById("formAvaliar");
  if (!form) return;

  var campos = ["comunicacao", "pontualidade", "repertorio"];

  function marcarNota(nome, valor) {
    var radios = form.querySelectorAll('input[name="' + nome + '"]');
    radios.forEach(function (radio) {
      radio.checked = String(radio.value) === String(valor);
    });
  }

  function atualizarPreviaNota() {
    var preview = document.getElementById("notaFinalPreview");
    if (!preview) return;
    var valores = campos.map(function (nome) {
      var marcado = form.querySelector('input[name="' + nome + '"]:checked');
      return marcado ? parseInt(marcado.value, 10) : null;
    });
    if (valores.indexOf(null) >= 0) {
      preview.textContent = "—";
      return;
    }
    var media = valores.reduce(function (soma, n) { return soma + n; }, 0) / 3;
    preview.textContent = media.toFixed(1);
  }

  window.abrirModalAvaliar = function (botao) {
    var dados = botao.dataset;
    form.action = dados.url;
    document.getElementById("avTitulo").textContent =
      (dados.edicao === "1" ? "Editar avaliação de " : "Avaliar ") + dados.participante;
    campos.forEach(function (nome) { marcarNota(nome, dados[nome]); });
    document.getElementById("avComentario").value = dados.comentario || "";
    atualizarPreviaNota();
    window.QVModal.abrir("mAvaliar");
  };

  form.addEventListener("change", atualizarPreviaNota);
})();
