(function () {
  function rotuloDoErro(erro) {
    var campo = erro.closest(".field") || erro.closest(".check");
    if (campo) {
      var label = campo.querySelector("label");
      if (label) return label.textContent.replace(/\*\s*$/, "").trim();
    }
    return null;
  }

  document.addEventListener("DOMContentLoaded", function () {
    var container = document.getElementById("flash-erros");
    var erros = document.querySelectorAll("p.erro");
    if (!container || !erros.length) return;

    var itens = [];
    erros.forEach(function (erro) {
      var texto = erro.textContent.trim();
      if (texto) itens.push({ rotulo: rotuloDoErro(erro), texto: texto });
    });
    if (!itens.length) return;

    var card = document.createElement("div");
    card.className = "flash-card";

    var titulo = document.createElement("h4");
    titulo.appendChild(document.createTextNode("Corrija os campos destacados"));
    var fechar = document.createElement("button");
    fechar.type = "button";
    fechar.className = "flash-close";
    fechar.setAttribute("aria-label", "Fechar aviso");
    fechar.textContent = "×";
    fechar.addEventListener("click", function () { card.remove(); });
    titulo.appendChild(fechar);
    card.appendChild(titulo);

    var lista = document.createElement("ul");
    itens.forEach(function (item) {
      var li = document.createElement("li");
      if (item.rotulo) {
        var b = document.createElement("b");
        b.textContent = item.rotulo + ": ";
        li.appendChild(b);
      }
      li.appendChild(document.createTextNode(item.texto));
      lista.appendChild(li);
    });
    card.appendChild(lista);
    container.appendChild(card);
  });
})();
