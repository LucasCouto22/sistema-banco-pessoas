function qvCsrfToken() {
  var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

async function revelarCampoPII(botao) {
  var alvo = document.getElementById(botao.dataset.alvo);
  if (!alvo) return;

  if (alvo.dataset.revelado === "1") {
    alvo.textContent = alvo.dataset.mascarado;
    alvo.dataset.revelado = "0";
    botao.setAttribute("aria-label", "Revelar");
    return;
  }

  if (alvo.dataset.valor) {
    alvo.textContent = alvo.dataset.valor;
    alvo.dataset.revelado = "1";
    botao.setAttribute("aria-label", "Ocultar");
    return;
  }

  botao.disabled = true;
  try {
    var resposta = await fetch(botao.dataset.url, {
      method: "POST",
      headers: { "X-CSRFToken": qvCsrfToken() },
    });
    if (!resposta.ok) {
      alvo.textContent = "Sem permissão";
      return;
    }
    var dados = await resposta.json();
    alvo.dataset.valor = dados.valor;
    alvo.textContent = dados.valor;
    alvo.dataset.revelado = "1";
    botao.setAttribute("aria-label", "Ocultar");
  } finally {
    botao.disabled = false;
  }
}
