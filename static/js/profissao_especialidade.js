/* Mostra o campo "Especialidade" só quando a profissão escolhida tiver uma
 * (marcado via `data-especialidade="1"` em cada <option>, gerado pelo widget
 * `SelectProfissao` no servidor). Usa delegação de evento e casa os nomes
 * por sufixo ("profissao" / "-profissao") pra funcionar tanto no formulário
 * simples (name="profissao") quanto no formset do wizard manual
 * (name="form-0-profissao", "form-1-profissao"...) sem código por linha. */
(function () {
  function campoEspecialidade(selectProfissao) {
    var nomeEspecialidade = selectProfissao.name.replace(/profissao$/, "especialidade");
    return document.querySelector('[name="' + nomeEspecialidade + '"]');
  }

  function atualizar(selectProfissao) {
    var campo = campoEspecialidade(selectProfissao);
    if (!campo) return;
    var wrapper = campo.closest(".field") || campo.parentElement;
    var opcao = selectProfissao.options[selectProfissao.selectedIndex];
    var temEspecialidade = !!(opcao && opcao.dataset.especialidade === "1");
    if (wrapper) wrapper.style.display = temEspecialidade ? "" : "none";
    if (!temEspecialidade) campo.value = "";
  }

  function ehSelectProfissao(el) {
    return el && el.tagName === "SELECT" && /(^|-)profissao$/.test(el.name || "");
  }

  document.addEventListener("change", function (evento) {
    if (ehSelectProfissao(evento.target)) atualizar(evento.target);
  });

  document.querySelectorAll("select").forEach(function (select) {
    if (ehSelectProfissao(select)) atualizar(select);
  });
})();
