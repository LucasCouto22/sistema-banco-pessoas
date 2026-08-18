/* Dashboard "Visão por segmento" — igual ao dashboard "Visão participantes"
   (ver static/js/dashboard.js), roda 100% no cliente a partir do mesmo JSON
   de participantes (core/dashviz.py::dados_participantes_dashboard), sem
   recarregar a página a cada troca de segmento — é isso que estava faltando
   na versão anterior (cada clique num segmento recarregava a página inteira
   via querystring, exatamente o mesmo problema que a Visão participantes
   tinha antes de virar interativa). */
(function () {
  "use strict";

  var elDados = document.getElementById("dados-participantes");
  if (!elDados) return;
  var dados = JSON.parse(elDados.textContent);
  var elCategorias = document.getElementById("categorias-disponiveis");
  var elFaixasRenda = document.getElementById("faixas-renda-disponiveis");
  var elGeneros = document.getElementById("generos-disponiveis");

  // Categorias de formulário cadastradas (Configurações de Formulários ›
  // Categorias) — substituem os antigos "segmentos" fixos do Projeto. Cor
  // por posição numa paleta que se repete, já que a lista agora é dinâmica.
  var SEGMENTOS = elCategorias ? JSON.parse(elCategorias.textContent) : [];
  var SEG_PALETA = ["#149A5B", "#F2295B", "#D98A0F", "#3B6FD4", "#0F8B8D", "#9B59B6", "#E8590C", "#8A7078"];
  function corSeg(s) { return SEG_PALETA[SEGMENTOS.indexOf(s) % SEG_PALETA.length]; }
  // Opções de `Participante.Genero` cadastradas — mesma ideia de SEGMENTOS,
  // pra não ficar hardcoded e descolar de novo se as opções mudarem.
  var GEN_ORDEM = elGeneros ? JSON.parse(elGeneros.textContent) : [];
  var GEN_PALETA = ["var(--violet)", "var(--blue)", "var(--pink)", "var(--amber)", "var(--green)", "#9B59B6", "#C9BEC2"];
  function corGen(g) { return GEN_PALETA[GEN_ORDEM.indexOf(g) % GEN_PALETA.length]; }
  // Faixas de renda individual cadastradas (a pergunta "Renda individual" do
  // formulário) — [[codigo, rótulo], ...] na ordem A→E, uma barra por faixa.
  var CLS_ORDEM = elFaixasRenda ? JSON.parse(elFaixasRenda.textContent) : [];
  var CLS_LABEL = {};
  CLS_ORDEM.forEach(function (par) { CLS_LABEL[par[0]] = par[1]; });
  var FX_ORDEM = ["18-24", "25-34", "35-44", "45-54", "55+"];
  var PROF_PALETA = ["#F2295B", "#3B6FD4", "#149A5B", "#D98A0F", "#9B59B6", "#0F8B8D", "#E8590C", "#8A7078"];

  var segSel = SEGMENTOS.filter(function (s) {
    return dados.some(function (p) { return p.cats.indexOf(s) >= 0; });
  })[0] || SEGMENTOS[0];

  function $(id) { return document.getElementById(id); }
  function fmt(n) { return n.toLocaleString("pt-BR"); }
  function contar(arr, campo) {
    var m = {};
    arr.forEach(function (p) { var v = p[campo]; if (v) m[v] = (m[v] || 0) + 1; });
    return m;
  }
  function maiorPar(mapa) {
    var chaves = Object.keys(mapa);
    if (!chaves.length) return null;
    chaves.sort(function (a, b) { return mapa[b] - mapa[a]; });
    return [chaves[0], mapa[chaves[0]]];
  }

  function selSeg(s) { segSel = s; render(); }
  window.QVDashSeg = { selSeg: selSeg };

  function render() {
    var porSeg = {};
    SEGMENTOS.forEach(function (s) {
      porSeg[s] = dados.filter(function (p) { return p.cats.indexOf(s) >= 0; }).length;
    });

    $("segTabs").innerHTML = SEGMENTOS.map(function (s) {
      return '<button class="seg-tab ' + (s === segSel ? "sel" : "") + '" onclick="QVDashSeg.selSeg(\'' + s +
        '\')"><span class="sw" style="background:' + corSeg(s) + '"></span>' + s +
        '<span class="ct">' + fmt(porSeg[s]) + "</span></button>";
    }).join("");

    var dadosSeg = dados.filter(function (p) { return p.cats.indexOf(segSel) >= 0; });
    var tot = dadosSeg.length;
    $("sgTotal").textContent = fmt(tot);
    $("sgPct").textContent = dados.length ? Math.round((tot / dados.length) * 100) + "% da base" : "—";

    var porCap = contar(dadosSeg, "cid");
    var topCap = maiorPar(porCap);
    $("sgCap").textContent = topCap ? topCap[0] : "—";
    $("sgCapFoot").textContent = topCap ? fmt(topCap[1]) + " participante(s) na categoria" : "—";

    var porGen = contar(dadosSeg, "gen");
    var topGen = maiorPar(porGen);
    $("sgGen").textContent = topGen ? topGen[0] : "—";
    $("sgGenFoot").textContent = topGen ? Math.round((topGen[1] / tot) * 100) + "% da categoria" : "—";

    var porCls = contar(dadosSeg, "cls");
    var topCls = maiorPar(porCls);
    $("sgCls").textContent = topCls ? (CLS_LABEL[topCls[0]] || topCls[0]) : "—";
    $("sgClsFoot").textContent = topCls ? Math.round((topCls[1] / tot) * 100) + "% da categoria" : "—";

    /* Comparativo entre categorias */
    var maxSeg = Math.max.apply(null, [1].concat(SEGMENTOS.map(function (s) { return porSeg[s]; })));
    $("sgComp").innerHTML = SEGMENTOS.map(function (s) {
      return '<button class="vbar ' + (s === segSel ? "sel" : "") + '" onclick="QVDashSeg.selSeg(\'' + s + '\')">' +
        '<span class="ct">' + fmt(porSeg[s]) + '</span><b style="height:' + Math.max(3, (porSeg[s] / maxSeg) * 100) +
        "%;background:" + corSeg(s) + '"></b><span>' + s + "</span></button>";
    }).join("");

    /* Top estados */
    var porUf = contar(dadosSeg, "uf");
    var topUfs = Object.keys(porUf).map(function (uf) { return [uf, porUf[uf]]; }).sort(function (a, b) { return b[1] - a[1]; }).slice(0, 6);
    var maxUf = Math.max.apply(null, [1].concat(topUfs.map(function (p) { return p[1]; })));
    $("sgUfs").innerHTML = topUfs.length
      ? topUfs.map(function (p) {
          return '<div class="hbar-row"><span class="lb">' + p[0] + '</span><div class="hbar"><i style="width:' +
            (p[1] / maxUf) * 100 + "%;background:" + corSeg(segSel) + '"></i></div><span class="ct">' +
            fmt(p[1]) + " · " + Math.round((p[1] / tot) * 100) + "%</span></div>";
        }).join("")
      : '<p class="empty" style="padding:8px 0">Sem dados de estado nesta categoria ainda.</p>';

    /* Gênero — barra empilhada + legenda (informativo, não filtra) */
    var stack = GEN_ORDEM.map(function (g) {
      var n = porGen[g] || 0;
      return '<i style="width:' + (tot ? (n / tot) * 100 : 0) + "%;background:" + corGen(g) + '" title="' + g + ": " + fmt(n) + '"></i>';
    }).join("");
    var legendGen = GEN_ORDEM.map(function (g) {
      var n = porGen[g] || 0;
      return '<span class="lg" style="cursor:default"><span class="sw" style="background:' + corGen(g) + '"></span>' + g +
        '<span class="ct">' + fmt(n) + " · " + (tot ? Math.round((n / tot) * 100) : 0) + "%</span></span>";
    }).join("");
    $("sgGenCh").innerHTML = '<div class="stackbar">' + stack + "</div><div class=\"legend\">" + legendGen + "</div>";

    /* Classe social — uma barra por faixa cadastrada (A-E) */
    var maxCls = Math.max.apply(null, [1].concat(CLS_ORDEM.map(function (par) { return porCls[par[0]] || 0; })));
    $("sgClsCh").innerHTML = CLS_ORDEM.map(function (par) {
      var codigo = par[0], rotulo = par[1];
      var n = porCls[codigo] || 0;
      return '<span class="vbar" style="cursor:default" title="' + rotulo + '"><span class="ct">' + fmt(n) +
        '</span><b style="height:' + Math.max(3, (n / maxCls) * 100) + "%;background:" + corSeg(segSel) +
        '"></b><span>' + codigo + "</span></span>";
    }).join("");

    /* Faixa etária */
    var porFx = contar(dadosSeg, "fx");
    var maxFx = Math.max.apply(null, [1].concat(FX_ORDEM.map(function (f) { return porFx[f] || 0; })));
    $("sgFxCh").innerHTML = FX_ORDEM.map(function (f) {
      var n = porFx[f] || 0;
      return '<span class="vbar" style="cursor:default"><span class="ct">' + fmt(n) + '</span><b style="height:' +
        Math.max(3, (n / maxFx) * 100) + "%;background:" + corSeg(segSel) + '"></b><span>' + f + "</span></span>";
    }).join("");

    /* Profissão — pizza (texto livre no cadastro: agrupa as 7 mais frequentes + "Outro") */
    var porProf = {};
    dadosSeg.forEach(function (p) { var k = p.prof || "Não informado"; porProf[k] = (porProf[k] || 0) + 1; });
    var pares = Object.keys(porProf).map(function (k) { return [k, porProf[k]]; }).sort(function (a, b) { return b[1] - a[1]; });
    var topProf = pares.slice(0, 7);
    var restoProf = pares.slice(7).reduce(function (s, p) { return s + p[1]; }, 0);
    if (restoProf > 0) topProf.push(["Outro", restoProf]);

    var angPr = 0;
    var fatiasProf = topProf.map(function (par, i) {
      var a0 = angPr, a1 = angPr + (tot ? (par[1] / tot) * 360 : 0);
      angPr = a1;
      return PROF_PALETA[i % PROF_PALETA.length] + " " + a0.toFixed(1) + "deg " + a1.toFixed(1) + "deg";
    });
    var legendaProf = topProf.map(function (par, i) {
      return '<span class="lg" style="cursor:default"><span class="sw" style="background:' + PROF_PALETA[i % PROF_PALETA.length] +
        '"></span>' + par[0] + '<span class="ct">' + fmt(par[1]) + " · " + (tot ? Math.round((par[1] / tot) * 100) : 0) + "%</span></span>";
    }).join("");
    $("sgProf").innerHTML = topProf.length
      ? '<div class="donut pie" style="background:conic-gradient(' + fatiasProf.join(",") + ')"></div><div class="donut-legend">' + legendaProf + "</div>"
      : '<p class="empty" style="padding:8px 0">Sem dados de profissão nesta categoria ainda.</p>';
  }

  render();
})();
