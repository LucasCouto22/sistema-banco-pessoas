(function () {
  function atualizarRotulo(container) {
    var marcados = container.querySelectorAll('.dropdown-multiselect-opcoes input[type="checkbox"]:checked');
    var rotulo = container.querySelector(".dropdown-multiselect-label");
    container.classList.toggle("tem-selecionados", marcados.length > 0);
    if (marcados.length === 0) {
      rotulo.textContent = "Selecione…";
    } else if (marcados.length === 1) {
      var texto = marcados[0].closest(".dropdown-multiselect-opcao").querySelector("span").textContent;
      rotulo.textContent = texto;
    } else {
      rotulo.textContent = marcados.length + " selecionadas";
    }
  }

  function fecharTodos(exceto) {
    document.querySelectorAll(".dropdown-multiselect.aberto").forEach(function (aberto) {
      if (aberto !== exceto) aberto.classList.remove("aberto");
    });
  }

  function normalizar(texto) {
    return texto
      .toLowerCase()
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "");
  }

  function iniciar(container) {
    var trigger = container.querySelector(".dropdown-multiselect-trigger");
    var busca = container.querySelector(".dropdown-multiselect-busca");
    var vazio = container.querySelector(".dropdown-multiselect-vazio");
    var opcoes = container.querySelectorAll(".dropdown-multiselect-opcao");

    atualizarRotulo(container);

    trigger.addEventListener("click", function (evento) {
      evento.stopPropagation();
      var estaAberto = container.classList.contains("aberto");
      fecharTodos(container);
      container.classList.toggle("aberto", !estaAberto);
      if (!estaAberto && busca) {
        busca.value = "";
        opcoes.forEach(function (op) { op.classList.remove("oculta"); });
        if (vazio) vazio.hidden = true;
        setTimeout(function () { busca.focus(); }, 0);
      }
    });

    container.querySelectorAll('input[type="checkbox"]').forEach(function (caixa) {
      caixa.addEventListener("change", function () { atualizarRotulo(container); });
    });

    if (busca) {
      busca.addEventListener("click", function (evento) { evento.stopPropagation(); });
      busca.addEventListener("input", function () {
        var termo = normalizar(busca.value.trim());
        var algumVisivel = false;
        opcoes.forEach(function (op) {
          var texto = normalizar(op.querySelector("span").textContent);
          var bate = texto.indexOf(termo) !== -1;
          op.classList.toggle("oculta", !bate);
          if (bate) algumVisivel = true;
        });
        if (vazio) vazio.hidden = algumVisivel || termo === "";
      });
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".dropdown-multiselect").forEach(iniciar);
  });

  document.addEventListener("click", function (evento) {
    if (evento.target.closest(".dropdown-multiselect")) return;
    fecharTodos(null);
  });

  document.addEventListener("keydown", function (evento) {
    if (evento.key === "Escape") fecharTodos(null);
  });
})();
