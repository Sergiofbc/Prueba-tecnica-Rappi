/**
 * Lee rappi-output.json + uber-output.json y genera docs/dashboard-insights.html
 * con gráficos (Chart.js) y docs/insights-metrics.json con cifras agregadas.
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const RAPPI = path.join(__dirname, 'rappi-output.json');
const UBER = path.join(__dirname, 'uber-output.json');
const OUT_HTML = path.join(__dirname, 'docs', 'dashboard-insights.html');
const OUT_METRICS = path.join(__dirname, 'docs', 'insights-metrics.json');

function parseMxn(s) {
  if (s == null || s === '') return null;
  const m = String(s).match(/[\d.]+/);
  if (!m) return null;
  const n = parseFloat(m[0]);
  return Number.isFinite(n) ? n : null;
}

function parseUberFeeMxn(feeSummary) {
  if (!feeSummary) return null;
  const m = String(feeSummary).match(/MXN\s*([\d.]+)|\$\s*([\d.]+)/i);
  if (m) return parseFloat(m[1] || m[2]);
  if (/gratis|free|\b0\b/i.test(feeSummary)) return 0;
  return null;
}

function parseEtaMinutes(etaSummary) {
  if (!etaSummary) return null;
  const m = String(etaSummary).match(/(\d+)\s*[-–]\s*(\d+)/);
  if (m) return (parseInt(m[1], 10) + parseInt(m[2], 10)) / 2;
  const m2 = String(etaSummary).match(/(\d+)\s*min/i);
  return m2 ? parseInt(m2[1], 10) : null;
}

function shortLabel(s, n = 28) {
  const t = String(s);
  return t.length <= n ? t : `${t.slice(0, n)}…`;
}

function main() {
  if (!fs.existsSync(RAPPI) || !fs.existsSync(UBER)) {
    console.error('Faltan rappi-output.json o uber-output.json en la raíz del proyecto.');
    process.exit(1);
  }

  const rappi = JSON.parse(fs.readFileSync(RAPPI, 'utf8'));
  const uber = JSON.parse(fs.readFileSync(UBER, 'utf8'));

  const rappiByName = new Map(
    (rappi.products || []).map((p) => [p.name, p]),
  );

  const rows = [];
  for (const u of uber.products || []) {
    const rp = rappiByName.get(u.rappiProductName);
    if (!rp) continue;
    const pr = parseMxn(rp.price);
    const pu = u.priceMxn ?? parseMxn(u.price);
    if (pr == null || pu == null) continue;
    const delta = pr - pu;
    const deltaPct = pu !== 0 ? Math.round((delta / pu) * 1000) / 10 : null;
    rows.push({
      name: u.rappiProductName,
      short: shortLabel(u.rappiProductName, 26),
      rappiMxn: pr,
      uberMxn: pu,
      deltaMxn: Math.round(delta * 100) / 100,
      deltaPct,
      rappiDiscount: rp.discount ?? null,
      uberDiscount: u.discount ?? null,
      comparable:
        (u.matchScore ?? 1) >= 0.9 &&
        !String(u.uberProductName).includes('4 pzas') /* heurística: match débil nuggets */,
    });
  }

  const comparableRows = rows.filter((r) => r.comparable);
  const n = comparableRows.length || rows.length;
  const sumR = comparableRows.reduce((a, r) => a + r.rappiMxn, 0);
  const sumU = comparableRows.reduce((a, r) => a + r.uberMxn, 0);
  let rappiHigher = 0;
  let uberHigher = 0;
  let tie = 0;
  for (const r of comparableRows) {
    if (r.deltaMxn > 1) rappiHigher++;
    else if (r.deltaMxn < -1) uberHigher++;
    else tie++;
  }

  const rappiFee = rappi.delivery?.feeMxn ?? parseMxn(rappi.delivery?.feeFormatted);
  const uberFee =
    parseUberFeeMxn(uber.delivery?.feeSummary) ??
    parseMxn(uber.delivery?.feeSummary);
  const etaUber = parseEtaMinutes(uber.delivery?.etaSummary);

  const withRappiPromo = (rappi.products || []).filter((p) => p.discount).length;
  const withUberPromo = (uber.products || []).filter((p) => p.discount).length;

  const metrics = {
    generatedAt: new Date().toISOString(),
    geo: {
      address: rappi.address,
      note: 'Un solo punto (Polanco / JW Marriott). La variabilidad geográfica requiere más corridas.',
    },
    basket: {
      pairsCompared: rows.length,
      comparablePairs: comparableRows.length,
      avgRappiMxn: n ? Math.round((sumR / n) * 100) / 100 : null,
      avgUberMxn: n ? Math.round((sumU / n) * 100) / 100 : null,
      rappiPricedHigherCount: rappiHigher,
      uberPricedHigherCount: uberHigher,
      tieCount: tie,
    },
    fees: {
      rappiDeliveryMxn: rappiFee,
      uberDeliveryMxn: uberFee,
      serviceFeeNote:
        'Service fees no estandarizados en los JSON de scrape; revisar checkout en ambas apps.',
    },
    ops: {
      uberEtaMinutesMid: etaUber,
      rappiEtaMinutes: null,
      note: 'El scrape de Rappi no captura ETA explícito; ampliar pipeline.',
    },
    promos: {
      rappiProductsWithVisibleDiscount: withRappiPromo,
      rappiProductTotal: (rappi.products || []).length,
      uberProductsMatchedWithDiscount: withUberPromo,
      uberMatchedTotal: (uber.products || []).length,
    },
    rows: comparableRows.length ? comparableRows : rows,
  };

  fs.mkdirSync(path.dirname(OUT_HTML), { recursive: true });
  fs.writeFileSync(OUT_METRICS, JSON.stringify(metrics, null, 2), 'utf8');

  const chartLabels = metrics.rows.map((r) => r.short);
  const dataRappi = metrics.rows.map((r) => r.rappiMxn);
  const dataUber = metrics.rows.map((r) => r.uberMxn);
  const dataDeltaPct = metrics.rows.map((r) => r.deltaPct ?? 0);

  const heatRows = metrics.rows
    .map((r) => ({
      name: r.short,
      pct: r.deltaPct,
      color:
        r.deltaPct == null
          ? '#e5e7eb'
          : r.deltaPct > 15
            ? '#fecaca'
            : r.deltaPct > 5
              ? '#fde68a'
              : r.deltaPct < -5
                ? '#bbf7d0'
                : '#e0f2fe',
    }))
    .slice(0, 19);

  const html = `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Insights competitivos — Rappi vs Uber Eats</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <style>
    :root { font-family: 'Segoe UI', system-ui, sans-serif; color: #111827; background: #f9fafb; }
    body { margin: 0; padding: 1.5rem 2rem 3rem; max-width: 1200px; margin-inline: auto; }
    h1 { font-size: 1.5rem; font-weight: 650; }
    h2 { font-size: 1.1rem; margin-top: 2rem; color: #374151; }
    .meta { color: #6b7280; font-size: 0.9rem; margin-bottom: 1.5rem; }
    .kpis { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 0.75rem; margin: 1rem 0 2rem; }
    .kpi { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 0.85rem 1rem; }
    .kpi strong { display: block; font-size: 1.25rem; }
    .kpi span { font-size: 0.8rem; color: #6b7280; }
    .grid2 { display: grid; grid-template-columns: 1fr; gap: 2rem; }
    @media (min-width: 900px) { .grid2 { grid-template-columns: 1fr 1fr; } }
    .chart-box { background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 1rem 1rem 0.5rem; margin-bottom: 1rem; }
    canvas { max-height: 380px; }
    table.heat { width: 100%; border-collapse: collapse; font-size: 0.8rem; background: #fff; border-radius: 12px; overflow: hidden; border: 1px solid #e5e7eb; }
    table.heat th, table.heat td { padding: 0.45rem 0.65rem; text-align: left; border-bottom: 1px solid #f3f4f6; }
    table.heat th { background: #f9fafb; font-weight: 600; }
    .swatch { display: inline-block; width: 12px; height: 12px; border-radius: 3px; vertical-align: middle; margin-right: 6px; }
    footer { margin-top: 2rem; font-size: 0.8rem; color: #9ca3af; }
  </style>
</head>
<body>
  <h1>Informe visual — Posicionamiento Rappi vs Uber Eats (McDonald's)</h1>
  <p class="meta">Generado: ${metrics.generatedAt}<br/>Zona: una corrida en <code>Polanco</code> · Datos: <code>rappi-output.json</code> + <code>uber-output.json</code></p>

  <div class="kpis">
    <div class="kpi"><span>Pares comparables</span><strong>${metrics.basket.comparablePairs || metrics.basket.pairsCompared}</strong></div>
    <div class="kpi"><span>Precio medio lista (comparable)</span><strong>R $${metrics.basket.avgRappiMxn} · U $${metrics.basket.avgUberMxn}</strong></div>
    <div class="kpi"><span>Ítems más caros en Rappi (&gt;$1)</span><strong>${metrics.basket.rappiPricedHigherCount}</strong></div>
    <div class="kpi"><span>Empates (~$0 diff)</span><strong>${metrics.basket.tieCount}</strong></div>
    <div class="kpi"><span>Delivery fee Rappi</span><strong>${rappiFee != null ? '$' + rappiFee + ' MXN' : '—'}</strong></div>
    <div class="kpi"><span>Delivery fee Uber (texto scrape)</span><strong>${uberFee != null ? '$' + uberFee + ' MXN' : '—'}</strong></div>
    <div class="kpi"><span>ETA Uber (aprox.)</span><strong>${etaUber != null ? etaUber + ' min' : '—'}</strong></div>
    <div class="kpi"><span>Promos visibles Rappi (muestra)</span><strong>${withRappiPromo}/${(rappi.products || []).length}</strong></div>
  </div>

  <h2>1. Comparación de precios por ítem (barras agrupadas)</h2>
  <div class="chart-box"><canvas id="c1"></canvas></div>

  <div class="grid2">
    <div>
      <h2>2. Delta % precio (Rappi vs Uber)</h2>
      <p style="font-size:0.85rem;color:#6b7280;">Positivo = Rappi más caro que Uber para ese SKU.</p>
      <div class="chart-box"><canvas id="c2"></canvas></div>
    </div>
    <div>
      <h2>3. Fees de entrega (comparación directa)</h2>
      <div class="chart-box"><canvas id="c3"></canvas></div>
    </div>
  </div>

  <h2>4. Heatmap textual — brecha % por producto</h2>
  <table class="heat">
    <thead><tr><th>Producto</th><th>Δ % (Rappi vs Uber)</th></tr></thead>
    <tbody>
${heatRows
  .map(
    (r) =>
      `      <tr><td><span class="swatch" style="background:${r.color}"></span>${escapeHtml(r.name)}</td><td>${r.pct != null ? r.pct + '%' : '—'}</td></tr>`,
  )
  .join('\n')}
    </tbody>
  </table>

  <footer>Documento complementario al Informe de Insights en <code>docs/INFORME_INSIGHTS_COMPETITIVOS.md</code>. Exportar a PDF: imprimir desde el navegador o usar “Print to PDF”.</footer>

  <script>
    const L = ${JSON.stringify(chartLabels)};
    Chart.defaults.font.family = "'Segoe UI',system-ui,sans-serif";
    new Chart(document.getElementById('c1'), {
      type: 'bar',
      data: {
        labels: L,
        datasets: [
          { label: 'Rappi (MXN)', data: ${JSON.stringify(dataRappi)}, backgroundColor: 'rgba(234, 88, 12, 0.85)' },
          { label: 'Uber Eats (MXN)', data: ${JSON.stringify(dataUber)}, backgroundColor: 'rgba(37, 99, 235, 0.85)' }
        ]
      },
      options: {
        responsive: true,
        plugins: { legend: { position: 'top' } },
        scales: {
          x: { ticks: { maxRotation: 45, minRotation: 45, font: { size: 9 } } },
          y: { title: { display: true, text: 'MXN' } }
        }
      }
    });
    new Chart(document.getElementById('c2'), {
      type: 'bar',
      data: {
        labels: L,
        datasets: [{
          label: 'Δ % precio (Rappi − Uber) / Uber',
          data: ${JSON.stringify(dataDeltaPct)},
          backgroundColor: ${JSON.stringify(dataDeltaPct.map((d) => (d > 10 ? '#dc2626' : d < -5 ? '#16a34a' : '#ca8a04')))}
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { x: { title: { display: true, text: '%' } } }
      }
    });
    new Chart(document.getElementById('c3'), {
      type: 'bar',
      data: {
        labels: ['Rappi', 'Uber Eats'],
        datasets: [{ label: 'Delivery fee (MXN)', data: [${rappiFee ?? 'null'}, ${uberFee ?? 'null'}], backgroundColor: ['rgba(234, 88, 12, 0.9)', 'rgba(37, 99, 235, 0.9)'] }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, title: { display: true, text: 'MXN' } } }
      }
    });
  </script>
</body>
</html>`;

  fs.writeFileSync(OUT_HTML, html, 'utf8');
  console.log('Escrito:', OUT_HTML);
  console.log('Métricas:', OUT_METRICS);
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

main();
