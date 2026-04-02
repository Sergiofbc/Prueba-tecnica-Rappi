/**
 * Uber Eats MX: misma dirección / búsqueda que tu grabación.
 * Lee los nombres de producto en rappi-output.json, busca cada uno en el catálogo de Uber y
 * guarda SOLO los que se encontraron → uber-output.json.
 *
 * Uso: npm run uber
 * Ver UI: uber:headed
 */
import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const CONFIG = {
  address:
    process.env.UBER_ADDRESS ??
    'JW MARRIOTT HOTEL MEXICO CITY POLANCO, Calle Andrés Bello 29, Polanco IV Sección, 11550 Miguel Hidalgo, CDMX, México',
  restaurantQuery: process.env.UBER_SEARCH ?? 'mc',
  storeLinkName:
    process.env.UBER_STORE_LINK ??
    "McDonald's Lomas Plaza Americana • Comida rápida",
  /** Si lo defines, navega directo tras la dirección (evita depender del enlace de búsqueda). */
  storeUrl:
    process.env.UBER_STORE_URL ??
    'https://www.ubereats.com/mx/store/mcdonalds-lomas-plaza/lirUzHWMQ6iakIvNZ89Hqw?diningMode=DELIVERY&sc=SEARCH_SUGGESTION',
  rappiJsonPath:
    process.env.RAPPI_JSON ?? path.join(__dirname, 'rappi-output.json'),
  outFile: process.env.UBER_OUT ?? path.join(__dirname, 'uber-output.json'),
};

const debug = process.argv.includes('--debug');
const headed =
  process.argv.includes('--headed') || debug || process.env.UBER_HEADED === '1';

function step(msg) {
  const t = new Date().toLocaleTimeString('es-MX', { hour12: false });
  console.log(`[uber ${t}] ${msg}`);
}

function normalizeName(s) {
  return String(s)
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .toLowerCase()
    .replace(/[^a-z0-9áéíóúñü\s]/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function tokenSet(s) {
  const stop = new Set(['de', 'la', 'el', 'con', 'y', 'mediano', 'mediana', 'grande']);
  return new Set(
    normalizeName(s)
      .split(' ')
      .map((w) => w.replace(/[^a-z0-9ñ]/g, ''))
      .filter((w) => w.length > 1 && !stop.has(w)),
  );
}

function jaccardTokens(a, b) {
  const A = tokenSet(a);
  const B = tokenSet(b);
  if (!A.size || !B.size) return 0;
  let inter = 0;
  for (const t of A) if (B.has(t)) inter++;
  const union = A.size + B.size - inter;
  return union ? inter / union : 0;
}

function bestUberMatch(rappiName, uberItems) {
  let best = null;
  let bestScore = 0;
  const rn = normalizeName(rappiName);
  for (const u of uberItems) {
    const un = normalizeName(u.name);
    let score = jaccardTokens(rappiName, u.name);
    if (rn && un && (rn.includes(un) || un.includes(rn))) score = Math.max(score, 0.72);
    if (score > bestScore) {
      bestScore = score;
      best = u;
    }
  }
  return { item: best, score: bestScore };
}

/** Uber suele mandar MXN en centavos enteros (p. ej. 19900 → 199). */
function uberMinorUnitsToPesos(raw) {
  if (typeof raw !== 'number' || !Number.isFinite(raw)) return raw;
  if (raw >= 1000) return Math.round(raw) / 100;
  return raw;
}

function parseMxnNumberFromPrice(s) {
  if (s == null) return null;
  const t = String(s).replace(/[^\d.,]/g, '').replace(/,/g, '');
  const n = parseFloat(t);
  return Number.isFinite(n) ? n : null;
}

function parseAllJsonBodies(captured) {
  const out = [];
  for (const c of captured) {
    try {
      out.push({ url: c.url, body: JSON.parse(c.text.slice(0, 800_000)) });
    } catch {
      /* skip */
    }
  }
  return out;
}

function deepFindUberProducts(obj, acc, depth = 0) {
  if (!obj || depth > 22) return;
  if (Array.isArray(obj)) {
    for (const x of obj) deepFindUberProducts(x, acc, depth + 1);
    return;
  }
  if (typeof obj !== 'object') return;

  const name =
    obj.name ??
    obj.title ??
    obj.itemTitle ??
    obj.displayName ??
    obj.productName ??
    obj?.item?.title;

  let price =
    obj.price ??
    obj?.priceTagline?.text ??
    obj?.priceTagline?.accessibilityText ??
    obj?.pricing?.price ??
    obj?.price_bucket;

  if (typeof price === 'object' && price !== null) {
    price =
      price.amount ??
      price.value ??
      price.formattedValue ??
      price.text ??
      null;
  }

  const discount =
    obj.promoLabel ??
    obj.discount ??
    obj?.promotion?.text ??
    null;

  if (typeof name === 'string' && name.length > 2 && price != null) {
    let p = price;
    if (typeof p === 'string' && /^[\d.]+$/.test(p.trim())) p = Number(p.trim());
    if (typeof p === 'number') p = uberMinorUnitsToPesos(p);
    acc.push({
      name: String(name).trim(),
      priceRaw: p,
      discount: discount != null ? String(discount) : null,
    });
  }
  for (const k of Object.keys(obj)) deepFindUberProducts(obj[k], acc, depth + 1);
}

function collectEtaAndFeeHints(obj, acc, path = '', depth = 0) {
  if (!obj || depth > 24) return;
  if (Array.isArray(obj)) {
    for (let i = 0; i < obj.length; i++) collectEtaAndFeeHints(obj[i], acc, `${path}[${i}]`, depth + 1);
    return;
  }
  if (typeof obj !== 'object') return;

  for (const [k, v] of Object.entries(obj)) {
    const p = path ? `${path}.${k}` : k;
    const kl = k.toLowerCase();

    if (typeof v === 'string' && v.length < 120 && /\d/.test(v)) {
      if (
        /eta|min|minute|entrega|delivery|tiempo/i.test(kl) ||
        /\d+\s*[-–]?\s*\d*\s*min/i.test(v)
      ) {
        acc.push({ type: 'eta_string', path: p, value: v });
      }
    }

    if (typeof v === 'number' && v >= 0 && v < 5000) {
      if (
        /delivery|fee|service|charge|env[ií]o|shipping/i.test(kl) &&
        /cost|fee|price|amount|total/i.test(kl)
      ) {
        acc.push({ type: 'fee_number', path: p, value: v });
      }
      if (/eta|duration|minutes/i.test(kl) && v > 0 && v < 300) {
        acc.push({ type: 'eta_minutes', path: p, value: v });
      }
    }

    collectEtaAndFeeHints(v, acc, p, depth + 1);
  }
}

/** Si la API no expone ítems, intenta leer filas de menú visibles (botones / enlaces con nombre + $). */
function collectUberCatalogFromDom(page) {
  return page.evaluate(() => {
    const items = [];
    const seen = new Set();
    const roots = document.querySelectorAll('button, [role="button"], a[href*="item"], li');
    for (const el of roots) {
      const raw = el.innerText || '';
      const lines = raw
        .split('\n')
        .map((l) => l.trim())
        .filter(Boolean);
      if (lines.length < 2) continue;
      const priceLine = lines.find((l) => /\$\s*[\d.,]+/.test(l));
      if (!priceLine) continue;
      const pm = priceLine.match(/\$\s*([\d.,]+)/);
      if (!pm) continue;
      let priceVal = parseFloat(pm[1].replace(/,/g, ''));
      if (!Number.isFinite(priceVal) || priceVal <= 0) continue;
      if (priceVal >= 1000) priceVal = Math.round(priceVal) / 100;
      const nameLine = lines.find(
        (l) => l.length > 4 && l !== priceLine && !/^\$\s*[\d.,]+$/.test(l),
      );
      if (!nameLine) continue;
      const name = nameLine.slice(0, 220);
      const key = `${name.toLowerCase()}|${priceVal}`;
      if (seen.has(key)) continue;
      seen.add(key);
      items.push({ name, priceRaw: priceVal, discount: null });
    }
    return items;
  });
}

function pickDeliveryFromDom(page) {
  return page.evaluate(() => {
    const body = document.body?.innerText ?? '';
    const lines = body.split(/\n/).map((l) => l.trim()).filter(Boolean);

    let etaText = null;
    for (const line of lines) {
      if (/\d+\s*[-–]\s*\d+\s*min/i.test(line) || /\d+\s*min\b/i.test(line)) {
        if (/entrega|delivery|min|llega/i.test(line.toLowerCase()) || /^\d/.test(line)) {
          etaText = line;
          break;
        }
      }
    }

    let feeText = null;
    for (const line of lines) {
      const low = line.toLowerCase();
      if ((low.includes('envío') || low.includes('entrega') || low.includes('delivery')) && /\$|mxn|gratis|free/i.test(line)) {
        feeText = line;
        break;
      }
    }

    return { etaText, feeText, sampleHead: lines.slice(0, 40).join(' | ') };
  });
}

function loadRappiProductNames(pathname) {
  const raw = fs.readFileSync(pathname, 'utf8');
  const data = JSON.parse(raw);
  const products = Array.isArray(data.products) ? data.products : [];
  return products.map((p) => (typeof p?.name === 'string' ? p.name : '')).filter(Boolean);
}

function formatUberPrice(raw) {
  if (raw == null) return null;
  if (typeof raw === 'number') return `$${raw} MXN`;
  const s = String(raw);
  if (/\$|mxn/i.test(s)) return s;
  const n = parseMxnNumberFromPrice(s);
  if (n != null) return `$${n} MXN`;
  return s;
}

const MATCH_MIN_SCORE = Number(process.env.UBER_MATCH_MIN ?? 0.38);

async function main() {
  if (!fs.existsSync(CONFIG.rappiJsonPath)) {
    throw new Error(`No existe ${CONFIG.rappiJsonPath}. Ejecuta antes npm run scrape`);
  }

  const rappiNames = loadRappiProductNames(CONFIG.rappiJsonPath).slice(0, 20);
  if (!rappiNames.length) throw new Error('rappi-output.json no tiene nombres de producto.');

  const captured = [];
  step(`${rappiNames.length} nombres a buscar en Uber (desde ${CONFIG.rappiJsonPath})`);

  step(`Chromium (visible: ${headed ? 'sí' : 'no'}, lento: ${debug ? 'sí' : 'no'})…`);
  const browser = await chromium.launch({ headless: !headed, slowMo: debug ? 120 : 0 });
  const context = await browser.newContext({
    locale: 'es-MX',
    timezoneId: 'America/Mexico_City',
    viewport: { width: 1360, height: 900 },
  });
  const page = await context.newPage();

  page.on('response', async (res) => {
    try {
      const ct = res.headers()['content-type'] || '';
      if (!/json/i.test(ct)) return;
      const u = res.url();
      if (!/ubereats\.com|uber\.com/i.test(u)) return;
      const text = await res.text().catch(() => '');
      if (text.length < 80 || text.length > 3_000_000) return;
      captured.push({ url: u, contentType: ct, text });
    } catch {
      /* ignore */
    }
  });

  const wait = (ms) => new Promise((r) => setTimeout(r, ms));

  try {
    step('Abriendo ubereats.com/mx…');
    await page.goto('https://www.ubereats.com/mx', { waitUntil: 'domcontentloaded', timeout: 90000 });
    await wait(1200);

    step('Ingresando dirección…');
    const addr = page.getByRole('combobox', { name: 'Ingresa la dirección de' });
    await addr.click({ timeout: 20000 });
    await addr.fill(CONFIG.address);
    await wait(800);

    await page
      .getByTestId('location-result')
      .getByText('JW Marriott Hotel Mexico City', { exact: false })
      .click({ timeout: 25000 });

    await wait(2000);

    step(`Buscando restaurante: "${CONFIG.restaurantQuery}"…`);
    const search = page.getByTestId('search-input');
    await search.click({ timeout: 20000 });
    await search.fill(CONFIG.restaurantQuery);
    await wait(1200);

    step(`Abriendo tienda: ${CONFIG.storeLinkName.slice(0, 60)}…`);
    await page.getByRole('link', { name: CONFIG.storeLinkName }).click({ timeout: 25000 });
    await page.waitForLoadState('domcontentloaded').catch(() => {});
    await wait(1000);

    if (CONFIG.storeUrl && process.env.UBER_SKIP_FINAL_GOTO !== '1') {
      step('Abriendo URL final de tienda (entrega), como en tu grabación…');
      await page.goto(CONFIG.storeUrl, { waitUntil: 'domcontentloaded', timeout: 90000 });
    }

    await wait(3500);

    step('Desplazando menú y capturando respuestas…');
    for (let i = 0; i < 14; i++) {
      await page.mouse.wheel(0, 800);
      await wait(450);
    }
    await wait(2000);

    const domDelivery = await pickDeliveryFromDom(page);

    const parsed = parseAllJsonBodies(captured);
    const hints = [];
    for (const b of parsed) collectEtaAndFeeHints(b.body, hints);

    const uberRaw = [];
    for (const b of parsed) deepFindUberProducts(b.body, uberRaw);

    const byNorm = new Map();
    for (const u of uberRaw) {
      const k = normalizeName(u.name);
      if (!k) continue;
      if (!byNorm.has(k)) byNorm.set(k, u);
    }

    step(`Catálogo vía API (aprox.): ${byNorm.size} ítems · respuestas JSON: ${captured.length}`);

    if (byNorm.size < 12) {
      step('Pocos ítems por API; fusionando filas visibles del DOM…');
      const domRows = await collectUberCatalogFromDom(page);
      for (const row of domRows) {
        const k = normalizeName(row.name);
        if (!k || byNorm.has(k)) continue;
        byNorm.set(k, row);
      }
    }

    const uberCatalog = [...byNorm.values()].map((u) => ({
      name: u.name,
      price: formatUberPrice(u.priceRaw),
      priceNumber: parseMxnNumberFromPrice(formatUberPrice(u.priceRaw)),
      discount: u.discount,
    }));

    const etaCandidates = hints.filter((h) => h.type === 'eta_string' || h.type === 'eta_minutes');

    const primaryEta =
      etaCandidates.find((h) => /etaRange|modalityOptions\[0\]/i.test(h.path)) ?? etaCandidates[0];

    const etaSummary =
      domDelivery.etaText ??
      (primaryEta?.type === 'eta_string' ? primaryEta.value : null) ??
      (primaryEta?.type === 'eta_minutes' ? `${primaryEta.value} min` : null);
    const feeSummary = domDelivery.feeText;

    const products = [];
    const notFound = [];

    for (const rappiProductName of rappiNames) {
      const { item, score } = bestUberMatch(rappiProductName, uberCatalog);
      const ok = item != null && score >= MATCH_MIN_SCORE;
      if (!ok) {
        notFound.push(rappiProductName);
        continue;
      }
      products.push({
        rappiProductName,
        uberProductName: item.name,
        price: item.price,
        priceMxn: item.priceNumber,
        discount: item.discount,
        matchScore: Math.round(score * 1000) / 1000,
      });
    }

    if (notFound.length) {
      step(`No encontrados en Uber (${notFound.length}): ${notFound.join('; ')}`);
    }

    const payload = {
      generatedAt: new Date().toISOString(),
      sourceRappiJson: path.basename(CONFIG.rappiJsonPath),
      address: CONFIG.address,
      store: CONFIG.storeLinkName,
      delivery: {
        etaSummary,
        feeSummary,
      },
      products,
      meta: {
        namesQueriedFromRappi: rappiNames.length,
        foundOnUber: products.length,
        notFoundOnUber: notFound.length,
        notFoundNames: notFound,
        uberCatalogUniqueItems: uberCatalog.length,
        uberJsonResponses: captured.length,
      },
    };

    fs.writeFileSync(CONFIG.outFile, JSON.stringify(payload, null, 2), 'utf8');
    step(`Listo. ${products.length}/${rappiNames.length} encontrados → ${CONFIG.outFile}`);
  } finally {
    step('Cerrando navegador…');
    await browser.close();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
