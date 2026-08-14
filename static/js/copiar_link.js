(function () {
  "use strict";

  function mostrarBalao(botao, texto) {
    var existente = botao.querySelector(".balao-copiado");
    if (existente) existente.remove();
    var balao = document.createElement("span");
    balao.className = "balao-copiado";
    balao.textContent = texto;
    botao.style.position = "relative";
    botao.appendChild(balao);
    requestAnimationFrame(function () {
      balao.classList.add("visivel");
    });
    setTimeout(function () {
      balao.classList.remove("visivel");
      setTimeout(function () { balao.remove(); }, 200);
    }, 1600);
  }

  function copiarTexto(texto) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(texto);
    }
    // Fallback pra contexto sem `navigator.clipboard` (ex.: http sem TLS).
    return new Promise(function (resolve, reject) {
      var campo = document.createElement("textarea");
      campo.value = texto;
      campo.style.position = "fixed";
      campo.style.opacity = "0";
      document.body.appendChild(campo);
      campo.focus();
      campo.select();
      var copiou = false;
      try {
        copiou = document.execCommand("copy");
      } catch (erro) {
        copiou = false;
      }
      document.body.removeChild(campo);
      if (copiou) resolve();
      else reject(new Error("Não foi possível copiar."));
    });
  }

  document.addEventListener("click", function (evento) {
    var botao = evento.target.closest("[data-copiar]");
    if (!botao) return;
    var texto = botao.getAttribute("data-copiar");
    if (!texto) return;
    copiarTexto(texto)
      .then(function () { mostrarBalao(botao, "Link copiado!"); })
      .catch(function () { mostrarBalao(botao, "Não foi possível copiar."); });
  });
})();
