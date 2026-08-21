/* Dashboard "Visão participantes" — filtro e diagrama de Venn 100% no
   cliente, igual ao protótipo (renderDashPart/renderVenn/svgVenn2/svgVenn3
   em prototipo-qualyvortice-v14.html): os dados de cada participante são
   embutidos na página uma vez (ver core/dashviz.py::dados_participantes_dashboard)
   e todo clique só refiltra esse array local e redesenha — sem ida ao
   servidor, sem recarregar a página. */
(function () {
  "use strict";

  var elDados = document.getElementById("dados-participantes");
  if (!elDados) return;
  var dados = JSON.parse(elDados.textContent);
  var elCategorias = document.getElementById("categorias-disponiveis");
  var elFaixasRenda = document.getElementById("faixas-renda-disponiveis");
  var elFaixasRendaFamiliar = document.getElementById("faixas-renda-familiar-disponiveis");
  var elGeneros = document.getElementById("generos-disponiveis");
  var elUrlPessoa = document.getElementById("url-pessoa-template");
  var URL_PESSOA_TPL = elUrlPessoa ? elUrlPessoa.dataset.tpl : "";

  var TILES = {
    RR: [2, 0], AP: [4, 0],
    AM: [1, 1], PA: [3, 1], MA: [4, 1], CE: [5, 1], RN: [6, 1],
    AC: [0, 2], RO: [2, 2], MT: [3, 2], TO: [4, 2], PI: [5, 2], PB: [6, 2],
    GO: [3, 3], DF: [4, 3], BA: [5, 3], PE: [6, 3], AL: [7, 3],
    MS: [2, 4], MG: [4, 4], ES: [5, 4], SE: [6, 4],
    SP: [3, 5], RJ: [4, 5], PR: [3, 6], SC: [3, 7], RS: [3, 8],
  };

  var CAPITAIS = ["Rio de Janeiro", "São Paulo", "Brasília", "Fortaleza", "Salvador"];
  var CAP_COR = {
    "Rio de Janeiro": "#F2295B", "São Paulo": "#FF7A3D", "Brasília": "#FFB15C",
    "Fortaleza": "#3B6FD4", "Salvador": "#149A5B",
  };
  // Opções de `Participante.Genero` cadastradas — [rótulo, ...] na ordem do
  // model. Antes era uma lista fixa de 4 rótulos que sobrou de antes da
  // realinhada de opções com o BP.xlsx (hoje são 7); cor por posição numa
  // paleta que se repete, mesmo padrão de `corSeg`.
  var GEN_ORDEM = elGeneros ? JSON.parse(elGeneros.textContent) : [];
  var GEN_PALETA = ["var(--violet)", "var(--blue)", "var(--pink)", "var(--amber)", "var(--green)", "#9B59B6", "#C9BEC2"];
  function corGen(g) { return GEN_PALETA[GEN_ORDEM.indexOf(g) % GEN_PALETA.length]; }
  // Faixas de renda individual cadastradas em `Participante.FaixaRendaIndividual`
  // (a mesma pergunta "Renda individual" do formulário) — [[codigo, rótulo], ...]
  // na ordem A→E. O gráfico mostra uma barra por faixa (o rótulo completo vira
  // tooltip via `title`), em vez de juntar em buckets fixos como antes.
  var CLS_ORDEM = elFaixasRenda ? JSON.parse(elFaixasRenda.textContent) : [];
  var CLS_LABEL = {};
  CLS_ORDEM.forEach(function (par) { CLS_LABEL[par[0]] = par[1]; });
  // Mesma ideia, pra "Renda familiar" (`Participante.FaixaRendaFamiliar`) —
  // painel separado ("Classe social (renda familiar)"), mesmos códigos A-E
  // do individual mas com rótulo/escala diferente (salários mínimos).
  var CLSF_ORDEM = elFaixasRendaFamiliar ? JSON.parse(elFaixasRendaFamiliar.textContent) : [];
  var CLSF_LABEL = {};
  CLSF_ORDEM.forEach(function (par) { CLSF_LABEL[par[0]] = par[1]; });
  var FX_ORDEM = ["18-24", "25-34", "35-44", "45-54", "55+"];
  // Categorias de formulário cadastradas (Configurações de Formulários ›
  // Categorias) — substituem os antigos "segmentos" fixos do Projeto
  // (Saúde/Cosméticos/Alimentação/Banco/Tecnologia): a lista agora reflete
  // o cadastro de verdade, então a cor de cada uma é por posição (paleta
  // que se repete), não mais por nome fixo.
  var SEGMENTOS = elCategorias ? JSON.parse(elCategorias.textContent) : [];
  var SEG_PALETA = ["#149A5B", "#F2295B", "#D98A0F", "#3B6FD4", "#0F8B8D", "#9B59B6", "#E8590C", "#8A7078"];
  function corSeg(s) { return SEG_PALETA[SEGMENTOS.indexOf(s) % SEG_PALETA.length]; }
  var VENN_FONT = "'Plus Jakarta Sans',system-ui,sans-serif";
  var VENN_DEEP = "#C4143F", VENN_DARK = "#750A26";
  // Lista usada pelo `renderVenn()` no último redesenho — o modal de
  // pessoas (`abrirVennModal`) refiltra em cima dela na hora do clique, sem
  // precisar recalcular nada do zero nem guardar estado à parte.
  var vennDadosAtual = [];

  var filtros = { uf: null, gen: null, cls: null, clsf: null, fx: null, cid: null };
  var FILTRO_NOME = {
    uf: "Estado", gen: "Gênero", cls: "Classe (individual)", clsf: "Classe (familiar)",
    fx: "Faixa etária", cid: "Capital",
  };
  var vennSel = SEGMENTOS.filter(function (s) {
    return dados.some(function (p) { return p.cats.indexOf(s) >= 0; });
  }).slice(0, 3);

  function $(id) { return document.getElementById(id); }
  function fmt(n) { return n.toLocaleString("pt-BR"); }
  function esc(s) { var d = document.createElement("div"); d.textContent = s; return d.innerHTML; }
  function contar(arr, campo) {
    var m = {};
    arr.forEach(function (p) { var v = p[campo]; if (v) m[v] = (m[v] || 0) + 1; });
    return m;
  }
  function dadosFiltrados() {
    return dados.filter(function (p) {
      return Object.keys(filtros).every(function (d) { return !filtros[d] || p[d] === filtros[d]; });
    });
  }

  function toggleF(dim, val) {
    filtros[dim] = filtros[dim] === val ? null : val;
    render();
  }
  function limparFiltros() {
    Object.keys(filtros).forEach(function (k) { filtros[k] = null; });
    render();
  }
  function toggleVennSeg(s) {
    var i = vennSel.indexOf(s);
    if (i >= 0) vennSel.splice(i, 1);
    else if (vennSel.length < 3) vennSel.push(s);
    renderVenn(dadosFiltrados());
  }
  function abrirVennModal(padrao) {
    var bits = padrao.split("");
    var pessoas = vennDadosAtual.filter(function (p) {
      var presente = vennSel.map(function (s) { return p.cats.indexOf(s) >= 0; });
      if (!presente.some(Boolean)) return false;
      return presente.map(function (b) { return b ? "1" : "0"; }).join("") === padrao;
    });

    var presentes = [], ausentes = [];
    vennSel.forEach(function (s, i) { (bits[i] === "1" ? presentes : ausentes).push(s); });
    var descricao = "em " + presentes.join(" e ") + (ausentes.length ? " (fora de " + ausentes.join(" e ") + ")" : "");
    $("vennModalTitulo").textContent = fmt(pessoas.length) + " participante(s) — " + descricao;

    $("vennModalCorpo").innerHTML = pessoas.length
      ? pessoas.map(function (p) {
          var href = URL_PESSOA_TPL.replace("/0/", "/" + p.id + "/");
          return "<tr><td data-label=\"Nome\">" + esc(p.nome) + "</td>" +
            "<td data-label=\"Estado\">" + esc(p.uf_nome || p.uf || "—") + "</td>" +
            "<td data-label=\"Idade\">" + (p.idade != null ? p.idade + " anos" : "—") + "</td>" +
            "<td><a class=\"btn btn-ghost btn-sm\" target=\"_blank\" rel=\"noopener\" href=\"" + href +
            "\">Ver pessoa</a></td></tr>";
        }).join("")
      : "<tr><td colspan=\"4\" class=\"empty\">Nenhum participante nessa combinação.</td></tr>";

    QVModal.abrir("mVennPessoas");
  }

  window.QVDash = {
    toggleF: toggleF, limparFiltros: limparFiltros, toggleVennSeg: toggleVennSeg, abrirVennModal: abrirVennModal,
  };

  function render() {
    var filtrados = dadosFiltrados();
    var tot = filtrados.length;

    if ($("dpTotal")) $("dpTotal").textContent = fmt(tot);
    if ($("dpTotalFoot")) $("dpTotalFoot").textContent = dados.length ? Math.round((tot / dados.length) * 100) + "% da base" : "";
    var emCaps = filtrados.filter(function (p) { return p.cid; }).length;
    if ($("dpCaps")) $("dpCaps").textContent = fmt(emCaps);
    if ($("dpCapsFoot")) {
      $("dpCapsFoot").textContent = tot
        ? Math.round((emCaps / tot) * 100) + "% do recorte · RJ, SP, Brasília, Fortaleza e Salvador"
        : "RJ · SP · Brasília · Fortaleza · Salvador";
    }

    var chips = Object.keys(filtros)
      .filter(function (d) { return filtros[d]; })
      .map(function (d) {
        var v = filtros[d];
        var texto = d === "cls" ? CLS_LABEL[v] || v : d === "clsf" ? CLSF_LABEL[v] || v : v;
        return '<button class="fchip" onclick="QVDash.toggleF(\'' + d + "','" + v + '\')"><small>' +
          FILTRO_NOME[d] + ":</small> " + esc(texto) + " ✕</button>";
      });
    $("fchips").innerHTML = chips.length
      ? '<span class="lbl">Filtros ativos:</span> ' + chips.join("") +
        ' <button class="fclear" onclick="QVDash.limparFiltros()">limpar tudo</button>'
      : '<span class="lbl">Nenhum filtro ativo — clique nos gráficos para segmentar a base.</span>';

    /* Mapa por estado */
    var porUf = contar(filtrados, "uf");
    var maxUf = Math.max.apply(null, [1].concat(Object.keys(porUf).map(function (k) { return porUf[k]; })));
    $("mapBR").innerHTML = Object.keys(TILES)
      .map(function (uf) {
        var pos = TILES[uf], n = porUf[uf] || 0;
        var al = n ? 0.12 + 0.83 * (n / maxUf) : 0.05;
        var claro = fundoEEscuro(al);
        return '<button class="tile ' + (filtros.uf === uf ? "sel" : "") + '" title="' + uf + ": " + fmt(n) +
          ' participante(s)" style="grid-column:' + (pos[0] + 1) + ";grid-row:" + (pos[1] + 1) +
          ";background:rgba(242,41,91," + al.toFixed(2) + ");color:" + (claro ? "#fff" : "#5C1F32") +
          '" onclick="QVDash.toggleF(\'uf\',\'' + uf + '\')"><b>' + uf + "</b><span>" + fmt(n) + "</span></button>";
      })
      .join("");

    /* Rosca — 5 principais capitais */
    var porCap = {};
    CAPITAIS.forEach(function (c) { porCap[c] = filtrados.filter(function (p) { return p.cid === c; }).length; });
    var totCaps = CAPITAIS.reduce(function (s, c) { return s + porCap[c]; }, 0);
    var ang = 0;
    var fatias = CAPITAIS.filter(function (c) { return porCap[c] > 0; }).map(function (c) {
      var a0 = ang, a1 = ang + (totCaps ? (porCap[c] / totCaps) * 360 : 0);
      ang = a1;
      return CAP_COR[c] + " " + a0.toFixed(1) + "deg " + a1.toFixed(1) + "deg";
    });
    var legendaCaps = CAPITAIS.map(function (c) {
      var n = porCap[c];
      return '<button class="lg ' + (filtros.cid === c ? "sel" : "") + '" onclick="QVDash.toggleF(\'cid\',\'' + c +
        '\')"><span class="sw" style="background:' + CAP_COR[c] + '"></span>' + c +
        '<span class="ct">' + fmt(n) + " · " + (totCaps ? Math.round((n / totCaps) * 100) : 0) + "%</span></button>";
    }).join("");
    $("chCaps").innerHTML =
      '<div class="donut" data-center="' + fmt(totCaps) + "\nnas capitais" + '"' +
      ' style="background:' + (totCaps ? "conic-gradient(" + fatias.join(",") + ")" : "#F1E4E8") + '"></div>' +
      '<div class="donut-legend">' + legendaCaps + "</div>";

    /* Gênero — barra empilhada + legenda */
    var porGen = contar(filtrados, "gen");
    var stack = GEN_ORDEM.map(function (g) {
      var n = porGen[g] || 0;
      return '<i style="width:' + (tot ? (n / tot) * 100 : 0) + "%;background:" + corGen(g) + '" title="' + g + ": " + fmt(n) + '"></i>';
    }).join("");
    var legendGen = GEN_ORDEM.map(function (g) {
      var n = porGen[g] || 0;
      return '<button class="lg ' + (filtros.gen === g ? "sel" : "") + '" onclick="QVDash.toggleF(\'gen\',\'' + g +
        '\')"><span class="sw" style="background:' + corGen(g) + '"></span>' + g +
        '<span class="ct">' + fmt(n) + " · " + (tot ? Math.round((n / tot) * 100) : 0) + "%</span></button>";
    }).join("");
    $("chGen").innerHTML = '<div class="stackbar">' + stack + "</div><div class=\"legend\">" + legendGen + "</div>";

    /* Classe social — barras verticais, uma por faixa cadastrada (A-E) */
    var porCls = contar(filtrados, "cls");
    var maxCls = Math.max.apply(null, [1].concat(CLS_ORDEM.map(function (par) { return porCls[par[0]] || 0; })));
    $("chCls").innerHTML = CLS_ORDEM.map(function (par) {
      var codigo = par[0], rotulo = par[1];
      var n = porCls[codigo] || 0;
      return '<button class="vbar ' + (filtros.cls === codigo ? "sel" : "") + '" title="' + esc(rotulo) +
        '" onclick="QVDash.toggleF(\'cls\',\'' + codigo + '\')">' +
        '<span class="ct">' + fmt(n) + '</span><b style="height:' + Math.max(3, (n / maxCls) * 100) + '%"></b><span>' + codigo + "</span></button>";
    }).join("");

    /* Classe social (renda familiar) — barras verticais, mesmo padrão da individual */
    var porClsf = contar(filtrados, "clsf");
    var maxClsf = Math.max.apply(null, [1].concat(CLSF_ORDEM.map(function (par) { return porClsf[par[0]] || 0; })));
    $("chClsFam").innerHTML = CLSF_ORDEM.map(function (par) {
      var codigo = par[0], rotulo = par[1];
      var n = porClsf[codigo] || 0;
      return '<button class="vbar ' + (filtros.clsf === codigo ? "sel" : "") + '" title="' + esc(rotulo) +
        '" onclick="QVDash.toggleF(\'clsf\',\'' + codigo + '\')">' +
        '<span class="ct">' + fmt(n) + '</span><b style="height:' + Math.max(3, (n / maxClsf) * 100) + '%"></b><span>' + codigo + "</span></button>";
    }).join("");

    /* Faixa etária — barras verticais */
    var porFx = contar(filtrados, "fx");
    var maxFx = Math.max.apply(null, [1].concat(FX_ORDEM.map(function (f) { return porFx[f] || 0; })));
    $("chFx").innerHTML = FX_ORDEM.map(function (f) {
      var n = porFx[f] || 0;
      return '<button class="vbar ' + (filtros.fx === f ? "sel" : "") + '" onclick="QVDash.toggleF(\'fx\',\'' + f + '\')">' +
        '<span class="ct">' + fmt(n) + '</span><b style="height:' + Math.max(3, (n / maxFx) * 100) + '%"></b><span>' + f + "</span></button>";
    }).join("");

    renderVenn(filtrados);
  }

  function fundoEEscuro(intensidade) {
    var r = 255 - 13 * intensidade, g = 255 - 214 * intensidade, b = 255 - 164 * intensidade;
    return 0.299 * r + 0.587 * g + 0.114 * b < 140;
  }

  function renderVenn(dadosAtuais) {
    var box = $("vennBox");
    if (!box) return;
    var dadosVenn = dadosAtuais || dadosFiltrados();
    vennDadosAtual = dadosVenn;

    $("vennPills").innerHTML = SEGMENTOS.map(function (s) {
      return '<button class="seg-tab ' + (vennSel.indexOf(s) >= 0 ? "sel" : "") + '" onclick="QVDash.toggleVennSeg(\'' + s +
        '\')"><span class="sw" style="background:' + corSeg(s) + '"></span>' + s + "</button>";
    }).join("");

    if (vennSel.length < 2) {
      box.innerHTML = '<p class="empty" style="padding:36px 20px">Selecione ao menos 2 categorias acima para ver quantos participantes atuam em mais de uma.</p>';
      $("vennFoot").textContent = "";
      return;
    }

    var counts = {};
    dadosVenn.forEach(function (p) {
      var presente = vennSel.map(function (s) { return p.cats.indexOf(s) >= 0; });
      if (!presente.some(Boolean)) return;
      var chave = presente.map(function (b) { return b ? "1" : "0"; }).join("");
      counts[chave] = (counts[chave] || 0) + 1;
    });
    var get = function (k) { return counts[k] || 0; };

    if (vennSel.length === 2) {
      var A = vennSel[0], B = vennSel[1];
      var onlyA = get("10"), onlyB = get("01"), both = get("11");
      box.innerHTML = svgVenn2(A, B, onlyA, onlyB, both);
      var totA = onlyA + both, totB = onlyB + both;
      $("vennFoot").textContent = fmt(both) + " participante(s) atuam em " + A + " e em " + B + " ao mesmo tempo — " +
        (totA ? Math.round((both / totA) * 100) : 0) + "% de quem está em " + A + " e " +
        (totB ? Math.round((both / totB) * 100) : 0) + "% de quem está em " + B + ".";
    } else {
      var Aa = vennSel[0], Bb = vennSel[1], Cc = vennSel[2];
      var oA = get("100"), oB = get("010"), oC = get("001");
      var ab = get("110"), ac = get("101"), bc = get("011"), abc = get("111");
      box.innerHTML = svgVenn3(Aa, Bb, Cc, oA, oB, oC, ab, ac, bc, abc);
      $("vennFoot").textContent = fmt(abc) + " participante(s) atuam nas três categorias ao mesmo tempo (" + Aa + ", " + Bb + " e " + Cc + ").";
    }
  }

  function vennDot(x, y, n, cor, raio, tam, padrao) {
    return '<g style="cursor:pointer" onclick="QVDash.abrirVennModal(\'' + padrao + '\')">' +
      '<circle cx="' + x + '" cy="' + y + '" r="' + raio + '" fill="#fff" fill-opacity=".88"/>' +
      '<text x="' + x + '" y="' + (y + 6) + '" text-anchor="middle" font-family="' + VENN_FONT +
      '" font-weight="800" font-size="' + tam + '" fill="' + cor + '">' + n + "</text></g>";
  }

  function svgVenn2(A, B, onlyA, onlyB, both) {
    var cA = corSeg(A), cB = corSeg(B);
    return '<svg viewBox="0 0 350 250" width="100%" style="max-width:420px;display:block;margin:0 auto">' +
      '<circle cx="135" cy="135" r="95" fill="' + cA + '" fill-opacity=".42" style="mix-blend-mode:multiply"/>' +
      '<circle cx="215" cy="135" r="95" fill="' + cB + '" fill-opacity=".42" style="mix-blend-mode:multiply"/>' +
      '<circle cx="135" cy="135" r="95" fill="none" stroke="' + cA + '" stroke-width="2"/>' +
      '<circle cx="215" cy="135" r="95" fill="none" stroke="' + cB + '" stroke-width="2"/>' +
      '<text x="95" y="22" text-anchor="middle" font-family="' + VENN_FONT + '" font-weight="800" font-size="13" fill="' + cA + '">' + esc(A) + "</text>" +
      '<text x="255" y="22" text-anchor="middle" font-family="' + VENN_FONT + '" font-weight="800" font-size="13" fill="' + cB + '">' + esc(B) + "</text>" +
      vennDot(85, 135, onlyA, cA, 19, 17, "10") + vennDot(265, 135, onlyB, cB, 19, 17, "01") +
      vennDot(175, 135, both, VENN_DEEP, 19, 17, "11") +
      "</svg>";
  }

  function svgVenn3(A, B, C, onlyA, onlyB, onlyC, ab, ac, bc, abc) {
    var cA = corSeg(A), cB = corSeg(B), cC = corSeg(C);
    return '<svg viewBox="0 0 380 320" width="100%" style="max-width:420px;display:block;margin:0 auto">' +
      '<circle cx="150" cy="140" r="100" fill="' + cA + '" fill-opacity=".38" style="mix-blend-mode:multiply"/>' +
      '<circle cx="230" cy="140" r="100" fill="' + cB + '" fill-opacity=".38" style="mix-blend-mode:multiply"/>' +
      '<circle cx="190" cy="205" r="100" fill="' + cC + '" fill-opacity=".38" style="mix-blend-mode:multiply"/>' +
      '<circle cx="150" cy="140" r="100" fill="none" stroke="' + cA + '" stroke-width="2"/>' +
      '<circle cx="230" cy="140" r="100" fill="none" stroke="' + cB + '" stroke-width="2"/>' +
      '<circle cx="190" cy="205" r="100" fill="none" stroke="' + cC + '" stroke-width="2"/>' +
      '<text x="105" y="24" text-anchor="middle" font-family="' + VENN_FONT + '" font-weight="800" font-size="13" fill="' + cA + '">' + esc(A) + "</text>" +
      '<text x="275" y="24" text-anchor="middle" font-family="' + VENN_FONT + '" font-weight="800" font-size="13" fill="' + cB + '">' + esc(B) + "</text>" +
      '<text x="190" y="312" text-anchor="middle" font-family="' + VENN_FONT + '" font-weight="800" font-size="13" fill="' + cC + '">' + esc(C) + "</text>" +
      vennDot(100, 108, onlyA, cA, 18, 15, "100") + vennDot(280, 108, onlyB, cB, 18, 15, "010") +
      vennDot(190, 272, onlyC, cC, 18, 15, "001") +
      vennDot(190, 92, ab, VENN_DEEP, 18, 15, "110") + vennDot(128, 195, ac, VENN_DEEP, 18, 15, "101") +
      vennDot(252, 195, bc, VENN_DEEP, 18, 15, "011") +
      vennDot(190, 168, abc, VENN_DARK, 18, 15, "111") +
      "</svg>";
  }

  render();
})();
