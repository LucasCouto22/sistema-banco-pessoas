/* Preenchimento de endereço nos formulários de participante (cadastro
   público e cadastro/edição interno): digitar o CEP busca o endereço na
   ViaCEP (bairro, cidade, UF) e, sempre que o estado é conhecido — vindo da
   ViaCEP ou escolhido manualmente —, a lista de cidades daquele estado é
   buscada na API de localidades do IBGE, em ordem alfabética
   (`orderBy=nome`), pra popular o <select> de Cidade. As duas são APIs
   públicas e gratuitas, sem chave de acesso. */
(function () {
  "use strict";

  var campoCep = document.getElementById("id_cep");
  var campoBairro = document.getElementById("id_bairro");
  var campoUf = document.getElementById("id_uf");
  var campoCidade = document.getElementById("id_cidade");
  if (!campoUf || !campoCidade) return;

  function apenasDigitos(valor) {
    return (valor || "").replace(/\D/g, "");
  }

  function popularCidades(uf, cidadeParaSelecionar) {
    campoCidade.disabled = true;
    campoCidade.innerHTML = '<option value="">Carregando…</option>';
    fetch("https://servicodados.ibge.gov.br/api/v1/localidades/estados/" + uf + "/municipios?orderBy=nome")
      .then(function (resposta) { return resposta.json(); })
      .then(function (municipios) {
        var opcoes = ['<option value="">Selecione…</option>'];
        municipios.forEach(function (m) {
          var selecionado = cidadeParaSelecionar && m.nome === cidadeParaSelecionar ? " selected" : "";
          opcoes.push('<option value="' + m.nome + '"' + selecionado + ">" + m.nome + "</option>");
        });
        campoCidade.innerHTML = opcoes.join("");
        campoCidade.disabled = false;
      })
      .catch(function () {
        campoCidade.innerHTML = '<option value="">Não foi possível carregar as cidades</option>';
        campoCidade.disabled = false;
      });
  }

  campoUf.addEventListener("change", function () {
    if (campoUf.value) {
      popularCidades(campoUf.value, null);
    } else {
      campoCidade.innerHTML = '<option value="">Selecione o estado primeiro</option>';
    }
  });

  if (campoCep) {
    campoCep.addEventListener("blur", function () {
      var cep = apenasDigitos(campoCep.value);
      if (cep.length !== 8) return;
      fetch("https://viacep.com.br/ws/" + cep + "/json/")
        .then(function (resposta) { return resposta.json(); })
        .then(function (dados) {
          if (dados.erro) return;
          if (campoBairro && dados.bairro) campoBairro.value = dados.bairro;
          if (dados.uf) {
            campoUf.value = dados.uf;
            popularCidades(dados.uf, dados.localidade || null);
          }
        })
        .catch(function () {});
    });
  }

  // Editando um participante que já tem UF preenchida: busca as cidades
  // desse estado de cara, mantendo a cidade atual selecionada (ela já veio
  // do servidor como única opção temporária, via `cidade.widget.choices`
  // em `ParticipanteForm.__init__`).
  if (campoUf.value) {
    popularCidades(campoUf.value, campoCidade.value);
  }
})();
