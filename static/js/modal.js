/* Modal genérico (overlay + caixa) — mesmo padrão visual do protótipo
   (`.overlay`/`.modal`), reescrito aqui porque o protótipo montava tudo em
   JS solto sem um "$"/"$$" equivalente neste projeto. Qualquer página pode
   usar: `QVModal.abrir("idDoOverlay")` / `QVModal.fechar("idDoOverlay")`. */
(function () {
  "use strict";

  function abrir(id) {
    var overlay = document.getElementById(id);
    if (overlay) overlay.classList.add("on");
  }

  function fechar(id) {
    var overlay = document.getElementById(id);
    if (overlay) overlay.classList.remove("on");
  }

  // Clique no fundo escuro (fora da caixa do modal) fecha.
  document.querySelectorAll(".overlay").forEach(function (overlay) {
    overlay.addEventListener("click", function (evento) {
      if (evento.target === overlay) overlay.classList.remove("on");
    });
  });

  // Esc fecha o modal que estiver aberto no momento.
  document.addEventListener("keydown", function (evento) {
    if (evento.key !== "Escape") return;
    document.querySelectorAll(".overlay.on").forEach(function (overlay) {
      overlay.classList.remove("on");
    });
  });

  window.QVModal = { abrir: abrir, fechar: fechar };
})();
