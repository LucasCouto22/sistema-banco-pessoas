/* Helpers compartilhados para os gráficos Chart.js do sistema (dashboards). */
var QV = (function () {
  function avisarFalhaCarregamento() {
    document.querySelectorAll(".chart-canvas-wrap").forEach(function (wrap) {
      if (wrap.dataset.avisado) return;
      wrap.dataset.avisado = "1";
      wrap.innerHTML =
        '<p class="empty" style="padding:0">Não foi possível carregar a biblioteca de gráficos ' +
        "(static/js/vendor/chart.umd.js). Verifique se o arquivo estático está publicado.</p>";
    });
  }

  function configurarPadroes() {
    if (typeof Chart === "undefined") {
      avisarFalhaCarregamento();
      return false;
    }
    Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
    Chart.defaults.font.size = 12;
    Chart.defaults.color = "#4A3A40";
    Chart.defaults.plugins.tooltip.backgroundColor = "#251A1E";
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
    Chart.defaults.plugins.tooltip.displayColors = false;
    return true;
  }

  var PALETA = {
    violeta: "#F2295B", violetaEscuro: "#C4143F", violetaClaro: "#FF6E8C",
    azul: "#3B6FD4", verde: "#149A5B", ambar: "#D98A0F", rosa: "#E8590C",
    grade: "#F1E4E8",
  };
  var CORES_CATEGORICAS = [PALETA.violeta, PALETA.azul, PALETA.verde, PALETA.ambar, PALETA.rosa, "#6C6584"];

  function lerDados(id) {
    var el = document.getElementById(id);
    return el ? JSON.parse(el.textContent) : null;
  }

  function gradienteHorizontal(corClara, corEscura) {
    return function (contexto) {
      var area = contexto.chart.chartArea;
      if (!area) return corEscura;
      var g = contexto.chart.ctx.createLinearGradient(area.left, 0, area.right, 0);
      g.addColorStop(0, corClara);
      g.addColorStop(1, corEscura);
      return g;
    };
  }

  function gradienteVertical(corClara, corEscura) {
    return function (contexto) {
      var area = contexto.chart.chartArea;
      if (!area) return corEscura;
      var g = contexto.chart.ctx.createLinearGradient(0, area.bottom, 0, area.top);
      g.addColorStop(0, corEscura);
      g.addColorStop(1, corClara);
      return g;
    };
  }

  function graficoBarraH(canvasId, dadosId, coresLista) {
    var dados = lerDados(dadosId);
    var canvas = document.getElementById(canvasId);
    if (!dados || !canvas || !dados.labels.length) return null;
    return new Chart(canvas, {
      type: "bar",
      data: {
        labels: dados.labels,
        datasets: [{
          data: dados.valores,
          backgroundColor: coresLista || gradienteHorizontal(PALETA.violetaClaro, PALETA.violeta),
          borderRadius: 6,
          barThickness: 14,
        }],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { beginAtZero: true, grid: { color: PALETA.grade }, ticks: { precision: 0 } },
          y: { grid: { display: false } },
        },
      },
    });
  }

  function graficoBarraV(canvasId, dadosId, coresLista) {
    var dados = lerDados(dadosId);
    var canvas = document.getElementById(canvasId);
    if (!dados || !canvas) return null;
    return new Chart(canvas, {
      type: "bar",
      data: {
        labels: dados.labels,
        datasets: [{
          data: dados.valores,
          backgroundColor: coresLista || gradienteVertical(PALETA.violetaClaro, PALETA.violeta),
          borderRadius: 8,
          maxBarThickness: 46,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, grid: { color: PALETA.grade }, ticks: { precision: 0 } },
          x: { grid: { display: false } },
        },
      },
    });
  }

  function graficoRosca(canvasId, dadosId, cores) {
    var dados = lerDados(dadosId);
    var canvas = document.getElementById(canvasId);
    if (!dados || !canvas || !dados.labels.length) return null;
    return new Chart(canvas, {
      type: "doughnut",
      data: {
        labels: dados.labels,
        datasets: [{
          data: dados.valores,
          backgroundColor: cores || CORES_CATEGORICAS,
          borderWidth: 2,
          borderColor: "#fff",
          hoverOffset: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "66%",
        plugins: {
          legend: {
            position: "right",
            labels: { boxWidth: 10, padding: 12, usePointStyle: true, pointStyle: "circle" },
          },
        },
      },
    });
  }

  function aoCarregar(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  return {
    PALETA: PALETA,
    CORES_CATEGORICAS: CORES_CATEGORICAS,
    configurarPadroes: configurarPadroes,
    lerDados: lerDados,
    graficoBarraH: graficoBarraH,
    graficoBarraV: graficoBarraV,
    graficoRosca: graficoRosca,
    aoCarregar: aoCarregar,
  };
})();
