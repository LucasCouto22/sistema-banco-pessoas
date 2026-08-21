/* Mostra o bloco "Escolha de categorias no cadastro público" só quando o
   tipo de perfil é "Captação" — pra "Respostas" essas opções não têm
   nenhum efeito (ver `pessoas/views.py::cadastro_publico`,
   `exige_escolha_categorias` já checa `perfil.tipo == Perfil.Tipo.CAPTACAO`
   antes de aplicar `qtd_categorias_escolha`), então não faz sentido nem
   mostrar o formulário pra preencher. */
(function () {
  "use strict";

  var select = document.getElementById("id_tipo");
  var bloco = document.getElementById("bloco-categorias-captacao");
  if (!select || !bloco) return;

  function atualizar() {
    bloco.style.display = select.value === "CAPTACAO" ? "" : "none";
  }

  select.addEventListener("change", atualizar);
  atualizar();
})();
