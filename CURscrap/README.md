# CURscrap — Comparativa Rappi vs Uber Eats (MX)

Proyecto de scraping con **Playwright** para fijar dirección, abrir la misma cadena (McDonald’s) en **Rappi** y **Uber Eats**, exportar menú y fees en JSON, y generar un **informe de insights competitivos** con dashboard HTML.

## Requisitos

- Node.js 18+
- Chromium (instalado vía Playwright)

## Instalación

```bash
cd CURscrap
npm install
npx playwright install chromium
```

## Flujo de datos

1. **`npm run scrape`** — Rappi MX: dirección, tienda, ~20 productos, delivery fee → `rappi-output.json`
2. **`npm run uber`** — Uber Eats MX: mismos nombres desde Rappi, busca en catálogo → solo coincidencias en `uber-output.json`
3. **`npm run report`** — Cruza ambos JSON → `docs/dashboard-insights.html` + `docs/insights-metrics.json`

### Scripts útiles

| Comando | Descripción |
|--------|-------------|
| `npm run scrape` | Rappi (headless) |
| `npm run scrape:headed` / `scrape:debug` | Ver navegador / pasos lentos |
| `npm run uber` | Uber + salida `uber-output.json` |
| `npm run uber:headed` / `uber:debug` | Igual con UI |
| `npm run report` | Regenera dashboard + métricas |

## Variables de entorno (opcional)

**Rappi:** `RAPPI_ADDRESS`, `RAPPI_STORE_SEARCH`, `RAPPI_STORE_LINK`, `RAPPI_MAX_PRODUCTS`, `RAPPI_OUT`, `RAPPI_HEADED`

**Uber:** `UBER_ADDRESS`, `UBER_SEARCH`, `UBER_STORE_LINK`, `UBER_STORE_URL`, `UBER_OUT`, `RAPPI_JSON`, `UBER_MATCH_MIN`, `UBER_SKIP_FINAL_GOTO`, `UBER_HEADED`

## Archivos generados

| Archivo | Contenido |
|---------|-----------|
| `rappi-output.json` | Delivery, productos (precio, descuento) |
| `uber-output.json` | Delivery (texto), productos encontrados alineados a nombres Rappi |
| `docs/dashboard-insights.html` | Gráficos (Chart.js): precios, delta %, fees, tabla tipo heatmap |
| `docs/insights-metrics.json` | Agregados numéricos para el informe |

## Informe ejecutivo (rúbrica)

El documento analítico está en:

**[`docs/INFORME_INSIGHTS_COMPETITIVOS.md`](docs/INFORME_INSIGHTS_COMPETITIVOS.md)**

Incluye análisis comparativo, top 5 insights accionables y referencias a las visualizaciones.

**Exportar a PDF:** abre `docs/dashboard-insights.html` en el navegador → Imprimir → “Guardar como PDF”. El informe Markdown puede pegarse en Notion o exportarse con herramientas tipo Pandoc si lo necesitas.

## Limitaciones

- Un snapshot por corrida; precios y promos cambian con hora y ubicación.
- **Variabilidad geográfica:** el scraper actual usa una dirección (Polanco / JW Marriott); comparar otras zonas requiere nuevas corridas con otra `RAPPI_ADDRESS` / `UBER_ADDRESS`.
- Los términos de uso de Rappi/Uber pueden restringir scraping automatizado; uso bajo tu responsabilidad.

## Licencia

Uso educativo / investigación. No afiliado a Rappi ni Uber.
