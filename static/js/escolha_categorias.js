document.addEventListener("DOMContentLoaded", function () {
  const contador = document.getElementById("categoriasContador");
  const botao = document.getElementById("btnContinuarCategorias");
  if (!contador || !botao) return;

  const limite = parseInt(contador.dataset.limite, 10);
  const checkboxes = Array.from(document.querySelectorAll('input[name="categorias"]'));

  function atualizar() {
    const marcados = checkboxes.filter((c) => c.checked);
    contador.textContent = marcados.length + " de " + limite + " selecionadas";
    const atingiuLimite = marcados.length >= limite;
    checkboxes.forEach((c) => {
      if (!c.checked) c.disabled = atingiuLimite;
    });
    botao.disabled = marcados.length !== limite;
  }

  checkboxes.forEach((c) => c.addEventListener("change", atualizar));
  atualizar();
});
