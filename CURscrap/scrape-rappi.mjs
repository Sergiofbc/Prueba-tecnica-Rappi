/**
 * Rappi MX: fija dirección, abre tienda y exporta envío + ~20 productos (prioriza Combos).
 * Uso: npm install && npx playwright install chromium && npm run scrape
 * Ver navegador: npm run scrape:headed
 * Navegador + pasos lentos: npm run scrape:debug
 */
import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const CONFIG = {
  address: process.env.RAPPI_ADDRESS ?? 'JW MARRIOTT HOTEL MEXICO CITY POLANCO, Calle Andrés Bello 29, Polanco IV Sección, 11550 Miguel Hidalgo, CDMX, México',
  storeSearch: process.env.RAPPI_STORE_SEARCH ?? 'mcdonal',
  storeLinkName: process.env.RAPPI_STORE_LINK ?? "mcdonald's mcdonald's",
  maxProducts: Number(process.env.RAPPI_MAX_PRODUCTS ?? 20),
  outFile: process.env.RAPPI_OUT ?? path.join(__dirname, 'rappi-output.json'),
};

const debug = process.argv.includes('--debug');
const headed =
  process.argv.includes('--headed') || debug || process.env.RAPPI_HEADED === '1';

function step(msg) {
  const t = new Date().toLocaleTimeString('es-MX', { hour12: false });
  console.log(`[rappi ${t}] ${msg}`);
}

function pickApiPayloads(captured) {
  const out = [];
  for (const c of captured) {
    const u = c.url.toLowerCase();
    if (
      /menu|catalog|product|store|restaurant|sku|offer|pricing|graphql/i.test(u) ||
      (c.contentType && /json/.test(c.contentType))
    ) {
      try {
        out.push({ url: c.url, body: JSON.parse(c.text.slice(0, 500_000)) });
      } catch {
        /* skip non-json */
      }
    }
  }
  return out;
}

function deepFindProducts(obj, acc, depth = 0) {
  if (!obj || depth > 18) return;
  if (Array.isArray(obj)) {
    for (const x of obj) deepFindProducts(x, acc, depth + 1);
    return;
  }
  if (typeof obj !== 'object') return;

  const name =
    obj.name ?? obj.product_name ?? obj.title ?? obj.nombre ?? obj.productName;
  const price =
    obj.price ??
    obj.final_price ??
    obj.unit_price ??
    obj.min_price ??
    obj.cost ??
    obj?.pricing?.price;
  const discount =
    obj.discount_percentage ??
    obj.percent_discount ??
    obj.discountPercent ??
    obj.descuento ??
    (typeof obj.discount === 'number' ? obj.discount : null);

  if (typeof name === 'string' && name.length > 2 && (price != null || obj.prices)) {
    acc.push({
      source: 'api_heuristic',
      name: String(name).trim(),
      price: price ?? obj.prices,
      discount: discount ?? null,
      raw: obj,
    });
  }
  for (const k of Object.keys(obj)) deepFindProducts(obj[k], acc, depth + 1);
}

/** Busca costo de envío en payloads JSON (GraphQL / REST). */
function collectDeliveryHints(obj, acc, path = '', depth = 0) {
  if (!obj || depth > 22) return;
  if (Array.isArray(obj)) {
    for (let i = 0; i < obj.length; i++) collectDeliveryHints(obj[i], acc, `${path}[${i}]`, depth + 1);
    return;
  }
  if (typeof obj !== 'object') return;

  for (const [k, v] of Object.entries(obj)) {
    const p = path ? `${path}.${k}` : k;
    const kl = k.toLowerCase();

    if (typeof v === 'number' && v >= 0 && v < 5000) {
      const looksDelivery =
        (/delivery|env[ií]o|ship|courier|transport/.test(kl) &&
          /cost|price|fee|amount|charge|total|value/.test(kl)) ||
        /^delivery_?fee$/.test(kl) ||
        /^shipping_?cost$/.test(kl);
      if (looksDelivery) acc.push({ path: p, value: v });
    }

    if (v && typeof v === 'object' && typeof v.amount === 'number' && /delivery|env[ií]o|ship|fee/i.test(kl)) {
      acc.push({ path: `${p}.amount`, value: v.amount });
    }

    collectDeliveryHints(v, acc, p, depth + 1);
  }
}

function pickDeliveryFromHints(hints) {
  if (!hints.length) return null;
  const scored = hints.map((h) => {
    const pl = h.path.toLowerCase();
    let score = 0;
    if (/store|restaurant|branch|shipping|checkout|basket|cart|quote/i.test(pl)) score += 3;
    if (/delivery|envio|envío|fee/i.test(pl)) score += 2;
    if (h.value > 0 && h.value <= 250) score += 1;
    return { ...h, score };
  });
  scored.sort((a, b) => b.score - a.score);
  const best = scored[0];
  return { amountMxn: best.value, sourcePath: best.path };
}

function parseAllJsonBodies(captured) {
  const out = [];
  for (const c of captured) {
    try {
      out.push({ url: c.url, body: JSON.parse(c.text.slice(0, 500_000)) });
    } catch {
      /* no json */
    }
  }
  return out;
}

/** Prioriza combos / McTrío / paquetes (como en tu flujo manual). */
function comboPriority(name) {
  const n = String(name).toLowerCase().normalize('NFD').replace(/\p{M}/gu, '');
  if (/mctrio|mc trio|paquete|cajita|combo|favoritos|exclusivo rappi|late\s*night/.test(n)) return 0;
  if (/\+/.test(n)) return 1;
  return 2;
}

function formatMxnPrice(v) {
  if (v == null) return null;
  if (typeof v === 'object') return JSON.stringify(v);
  const n = Number(v);
  if (!Number.isNaN(n)) return `$${n} MXN`;
  const s = String(v);
  return /\$/.test(s) ? s : `$${s} MXN`;
}

function formatDiscount(d) {
  if (d == null || d === '') return null;
  const n = Number(d);
  if (!Number.isNaN(n)) {
    if (n === 0) return null;
    if (n > 0 && n <= 100) return `${n}%`;
  }
  return String(d);
}

async function extractFromDom(page) {
  return page.evaluate(() => {
    const money = (s) => {
      if (!s) return null;
      const t = String(s).replace(/\s+/g, ' ').trim();
      const m = t.match(/\$[\d.,]+/);
      return m ? m[0] : null;
    };

    const deliveryHints = [
      'envío',
      'delivery',
      'entrega',
      'costo de envío',
      'tarifa',
    ];

    let deliveryText = null;
    const walker = document.body.innerText || '';
    for (const line of walker.split('\n')) {
      const low = line.toLowerCase();
      if (deliveryHints.some((h) => low.includes(h)) && /\$/.test(line)) {
        deliveryText = line.trim();
        break;
      }
    }

    /** @type {{ name: string, price: string | null, discount: string | null, section: string | null }[]} */
    const items = [];
    const seen = new Set();

    const sectionRoots = Array.from(
      document.querySelectorAll('h1, h2, h3, h4, [role="heading"]'),
    );

    const getSectionNear = (el) => {
      let n = el;
      for (let i = 0; i < 12 && n; i++) {
        const prev = n.previousElementSibling;
        if (prev) {
          const tag = prev.tagName?.toLowerCase();
          if (tag === 'h2' || tag === 'h3' || tag === 'h4')
            return prev.textContent?.trim() || null;
        }
        n = n.parentElement;
      }
      return null;
    };

    const candidates = Array.from(
      document.querySelectorAll('a[href*="product"], article, [data-testid], li'),
    ).filter((el) => {
      const txt = el.innerText || '';
      return txt.length > 10 && txt.length < 800 && /\$/.test(txt);
    });

    const comboFirst = (a, b) => {
      const ca = /combo/i.test(a.section || '') ? 0 : 1;
      const cb = /combo/i.test(b.section || '') ? 0 : 1;
      if (ca !== cb) return ca - cb;
      return 0;
    };

    for (const el of candidates) {
      const full = (el.innerText || '').replace(/\s+/g, ' ').trim();
      const lines = full.split(/\n/).map((l) => l.trim()).filter(Boolean);
      const nameLine =
        lines.find((l) => l.length > 3 && !/^\$/.test(l) && !/^%/.test(l)) || lines[0];
      if (!nameLine || nameLine.length < 3) continue;

      const price = money(full);
      if (!price) continue;

      let discount = null;
      const dm = full.match(/(\d+)\s*%|descuento|promo|oferta/i);
      if (dm) discount = dm[0];

      const section =
        getSectionNear(el) ||
        sectionRoots.find((h) => {
          const r = h.getBoundingClientRect();
          const er = el.getBoundingClientRect();
          return er.top > r.top && er.top - r.top < 400 && /combo|menú|menu|destac|popular/i.test(h.textContent || '');
        })?.textContent?.trim() ||
        null;

      const key = `${nameLine}|${price}`;
      if (seen.has(key)) continue;
      seen.add(key);

      items.push({
        name: nameLine.slice(0, 200),
        price,
        discount,
        section: section ? section.slice(0, 120) : null,
      });
    }

    items.sort(comboFirst);
    return { deliveryText, items };
  });
}

async function main() {
  const captured = [];

  step(`Iniciando Chromium (visible: ${headed ? 'sí' : 'no'}, lento: ${debug ? 'sí' : 'no'})…`);
  const browser = await chromium.launch({ headless: !headed, slowMo: debug ? 150 : 0 });
  const context = await browser.newContext({
    locale: 'es-MX',
    timezoneId: 'America/Mexico_City',
    viewport: { width: 1280, height: 900 },
  });
  const page = await context.newPage();

  page.on('response', async (res) => {
    try {
      const ct = res.headers()['content-type'] || '';
      if (!/json|graphql/i.test(ct)) return;
      const u = res.url();
      if (!/rappi/i.test(u)) return;
      const text = await res.text().catch(() => '');
      if (text.length < 50 || text.length > 2_000_000) return;
      captured.push({ url: u, contentType: ct, text });
    } catch {
      /* ignore */
    }
  });

  const v = (ms) => new Promise((r) => setTimeout(r, ms));

  try {
    step('Abriendo rappi.com.mx…');
    await page.goto('https://www.rappi.com.mx/', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await v(800);

    step('Ubicación: Ciudad de México + campo de dirección…');
    await page.getByRole('button', { name: 'Ciudad de México' }).click({ timeout: 15000 }).catch(() => {});
    await page
      .getByRole('textbox', { name: 'Escribe la dirección de' })
      .click({ timeout: 15000 });
    await page.getByRole('textbox', { name: 'Escribe la dirección de' }).fill(CONFIG.address);
    await v(600);
    step('Seleccionando sugerencia JW Marriott y confirmando…');
    await page.getByRole('button', { name: /JW MARRIOTT HOTEL MEXICO CITY/i }).click({ timeout: 20000 });
    await page.getByRole('button', { name: 'Confirmar Dirección' }).click({ timeout: 15000 });
    await page.getByRole('button', { name: 'Guardar dirección' }).click({ timeout: 15000 });
    await v(1500);

    step(`Buscando tienda: "${CONFIG.storeSearch}"…`);
    await page.getByRole('searchbox', { name: 'Comida, restaurantes, tiendas' }).click({ timeout: 15000 });
    await page.getByRole('searchbox', { name: 'Comida, restaurantes, tiendas' }).fill(CONFIG.storeSearch);
    await v(1000);

    step(`Abriendo enlace: ${CONFIG.storeLinkName}…`);
    const link = page.getByRole('link', { name: CONFIG.storeLinkName, exact: true });
    await link.click({ timeout: 20000 });
    await page.waitForLoadState('domcontentloaded').catch(() => {});
    await v(3000);

    step('Desplazando la página para cargar el menú…');
    for (let i = 0; i < 8; i++) {
      await page.mouse.wheel(0, 900);
      await v(500);
    }

    await v(2000);
    step('Extrayendo envío y productos desde DOM/API…');

    const dom = await extractFromDom(page);
    const parsedBodies = parseAllJsonBodies(captured);
    const apiSamples = pickApiPayloads(captured);

    const deliveryHints = [];
    for (const s of parsedBodies) collectDeliveryHints(s.body, deliveryHints);
    const deliveryFromApi = pickDeliveryFromHints(deliveryHints);

    const apiProducts = [];
    for (const s of apiSamples.slice(0, 40)) {
      deepFindProducts(s.body, apiProducts);
    }

    const mergedByName = new Map();
    for (const p of apiProducts) {
      const k = p.name.toLowerCase();
      if (!mergedByName.has(k)) mergedByName.set(k, p);
    }
    const sortedApi = [...mergedByName.values()].sort(
      (a, b) => comboPriority(a.name) - comboPriority(b.name),
    );
    const fromApi = sortedApi.slice(0, CONFIG.maxProducts);

    let products;
    if (fromApi.length >= 5) {
      products = fromApi.map((p) => ({
        name: p.name,
        price: formatMxnPrice(p.price),
        discount: formatDiscount(p.discount),
        section: null,
        source: 'api',
      }));
    } else {
      products = dom.items
        .slice()
        .sort((a, b) => comboPriority(a.name) - comboPriority(b.name))
        .slice(0, CONFIG.maxProducts)
        .map((p) => ({
          name: p.name,
          price: p.price || null,
          discount: p.discount,
          section: p.section,
          source: 'dom',
        }));
    }

    const payload = {
      scrapedAt: new Date().toISOString(),
      address: CONFIG.address,
      storeSearch: CONFIG.storeSearch,
      delivery: {
        feeMxn: deliveryFromApi?.amountMxn ?? null,
        feeFormatted:
          deliveryFromApi != null ? `$${deliveryFromApi.amountMxn} MXN` : null,
        apiField: deliveryFromApi?.sourcePath ?? null,
        domSnippet: dom.deliveryText,
        note:
          'Costo de envío a nivel tienda/pedido en esta sesión. Puede variar con promos, horario y distancia.',
      },
      products,
      meta: {
        domCandidates: dom.items.length,
        jsonBodiesParsed: parsedBodies.length,
        apiPayloadsMatched: apiSamples.length,
        apiProductHeuristicCount: apiProducts.length,
        deliveryHintsFound: deliveryHints.length,
      },
    };

    fs.writeFileSync(CONFIG.outFile, JSON.stringify(payload, null, 2), 'utf8');
    step(`Listo. JSON: ${CONFIG.outFile}`);
  } finally {
    step('Cerrando navegador…');
    await browser.close();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
