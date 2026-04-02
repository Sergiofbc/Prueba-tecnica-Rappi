# Informe de insights competitivos

**Rappi vs Uber Eats (México)** · McDonald’s · Entrega a domicilio  
**Documento ejecutivo para Strategy y Pricing**  
**Fuente de datos:** salidas automáticas `rappi-output.json` y `uber-output.json` (scraping Playwright)  
**Zona analizada:** una corrida — Polanco, CDMX (dirección tipo JW Marriott Polanco)  
**Fecha de métricas agregadas (generación):** ver `docs/insights-metrics.json` campo `generatedAt`

> **Nota metodológica:** Los hallazgos describen **esta muestra** (mismo restaurante, misma dirección, mismo instante). Para afirmar comportamiento nacional o por SES/zona hace falta replicar el pipeline en más geografías y ventanas de tiempo (bonus: tendencias temporales).

---

## 1. Resumen ejecutivo

En la muestra, **el listado de Rappi muestra precios medios más altos** en el conjunto de ítems comparables frente a Uber Eats, con **brechas muy fuertes en algunos paquetes / ítems combo** y **paridad** en buena parte de los McTríos “base”. **El fee de entrega** capturado es **más visible en Rappi ($30 MXN)** que en Uber en esta sesión (**$0 MXN** según texto “MXN0”). Sobre **promoción en menú**, Rappi muestra **etiquetas de descuento en 8 de 20** productos muestreados; en los **19** ítems emparejados en Uber **no apareció descuento** en el JSON exportado (puede haber promos en checkout o fuera del texto scrapeado).

**Visualizaciones:** abrir en navegador el archivo **`docs/dashboard-insights.html`** (3 gráficos principales + tabla tipo heatmap de brecha %). Métricas tabulares: **`docs/insights-metrics.json`**.

---

## 2. Análisis comparativo estructurado

### 2.1 Posicionamiento de precios (Rappi vs competencia)

**Métricas (pares comparables, n = 18; se excluye un match débil McNuggets 6 vs 4 piezas):**

| Indicador | Valor (muestra) |
|-----------|-----------------|
| Precio medio lista Rappi | **$238.83 MXN** |
| Precio medio lista Uber Eats | **$208.89 MXN** |
| Ítems con Rappi **más caro** (> $1 vs Uber) | **9** |
| Ítems en **paridad** (~ $0 diferencia) | **9** |
| Ítems con Uber **más caro** (> $1 vs Rappi) | **0** |

**Lectura:** Rappi aparece **más caro o igual** en esta canasta; no hubo SKUs comparables donde Uber superara a Rappi en precio de lista en la muestra. Las mayores brechas concentran en **paquetes / bundles** (p. ej. “Paquete Me encanta”, “Paquete Botanero”, “Big Mac Tocino + favoritos”) según filas en `insights-metrics.json`.

**Implicación:** El posicionamiento no es uniforme: hay **ancla de paridad en McTríos** y **presión competitiva en bundles**, donde Uber muestra listas más bajas.

---

### 2.2 Ventaja / desventaja operacional (tiempos de entrega)

| Plataforma | Dato en scrape | Limitación |
|------------|----------------|------------|
| **Uber Eats** | ~**17 min** (texto tipo ETA en DOM/API; rango en payload pudo ser mayor) | Un solo valor de sesión |
| **Rappi** | **No capturado** en el JSON actual | El pipeline Rappi no extrajo ETA explícito |

**Lectura:** En esta corrida **solo Uber aporta señal operacional directa** sobre tiempo prometido. **No se puede concluir** quién entrega más rápido sin **simetría de datos** (añadir ETA Rappi al scraper o medición post-compra).

---

### 2.3 Estructura de fees (delivery y service)

| Concepto | Rappi (muestra) | Uber Eats (muestra) |
|----------|-----------------|---------------------|
| **Delivery fee** | **$30 MXN** (`feeMxn`) | **$0 MXN** (parseado de “Costo de envío a MXN0” en texto) |
| **Service fee / comisión plataforma** | No en JSON | No en JSON |

**Lectura:** La **comparación de delivery fee** favorece a Uber en esta sesión (0 vs 30). Los **service fees** suelen aparecer al **checkout**; los JSON de menú **no sustituyen** un análisis de “precio final pagado”.

**Recomendación metodológica:** Completar con **carrito de prueba** o scraper de checkout (respetando ToS) para fee total.

---

### 2.4 Estrategia promocional

| Plataforma | Señal en datos |
|------------|----------------|
| **Rappi** | **8 / 20** productos con **descuento % visible** en listado (p. ej. 39%, 35%, 23%) |
| **Uber Eats** | **0 / 19** ítems emparejados con campo `discount` en `uber-output.json` |

**Lectura:** Rappi **comunica más promoción en ficha de menú** en esta muestra. Uber puede estar **descontando fuera del texto scrapeado** (cupones, Uber One, precio post-modificador). **No confundir** “sin etiqueta en JSON” con “sin promo real”.

---

### 2.5 Variabilidad geográfica

**Estado:** Con **una sola dirección** (Polanco / alta densidad), **no es posible** afirmar si la competitividad cambia en **periferia, NSE bajo, o ciudades secundarias**.

**Finding preliminar:** La muestra es **solo CBD-style**; cualquier insight sobre “zonas periféricas” requiere **datos adicionales** (re-ejecutar con otras coords o grid de direcciones).

---

## 3. Top 5 insights accionables

### Insight 1 — Bundles con brecha extrema en lista

- **Finding:** En ítems como **“Big Mac Tocino + favoritos”** y **“Paquete Me encanta”**, Rappi muestra **precios de lista muy superiores** a Uber (+**64.8%** y +**79.8%** vs Uber en esta muestra, ver `insights-metrics.json`).
- **Impacto:** Los usuarios que comparan **solo listado** pueden percibir a Rappi como **caro en los heroes de canasta**; riesgo de **abandono** y presión en **márgenes** si solo se corrige con descuento agresivo sin comunicar valor.
- **Recomendación:** Auditoría de **pricing display** vs **precio efectivo post-promo**; alinear **ancla psicológica** con Uber en 3–5 SKUs críticos o clarificar **precio tachado / ahorro** en UI; negociación con marca para **paridad de bundle** en zonas de alta elasticidad.

---

### Insight 2 — Paridad en McTríos “base” (con excepciones)

- **Finding:** Varios **McTríos** (Hamb sencilla/doble/triple, Spicy, línea Mario Galaxy) muestran **paridad** frente a Uber; **excepción** en esta muestra: **McTrío mediano McPollo**, donde la lista en Rappi es **~16% mayor** que en Uber.
- **Impacto:** Rappi **no está desalineado en todo el menú**; el problema es **heterogéneo** → las tácticas deben ser **SKU-specific**, no un “ajuste global”.
- **Recomendación:** Segmentar pricing por **familia de producto**; reservar presupuesto promocional para **SKUs con mayor brecha** en lugar de descuentos horizontales.

---

### Insight 3 — Fee de entrega visible

- **Finding:** **$30 MXN** Rappi vs **$0** Uber en la captura de fee de envío.
- **Impacto:** En **ticket bajo**, $30 es **un fricción material** vs competidor con envío mostrado en cero; puede **sesgar** la decisión aunque el total final dependa de suscripciones u otros cargos.
- **Recomendación:** Experimentos A/B de **fee reducido** en horas valle o **bundling con Rappi Prime**; comunicar **fee inclusivo** vs competencia en microcopy; monitorear **CEV por cohorte** cuando Uber sea 0.

---

### Insight 4 — Estrategia de promoción comunicada

- **Finding:** Rappi muestra **más descuentos explícitos en listado** (8/20) que los emparejados en Uber en JSON (0/19).
- **Impacto:** Rappi puede verse **“en promoción constante”**; si el **precio neto** no acompaña, hay riesgo de **desconfianza**. Si Uber desplaza promo al checkout, Rappi queda en desventaja en **percepción de “lista limpia”**.
- **Recomendación:** Test de **precio regular vs promo** en search; estudio cualitativo de **cómo ve el usuario Uber sin etiquetas**; alinear con marketing **reglas de communicated savings**.

---

### Insight 5 — Hueco de datos (ETA y geografía)

- **Finding:** **Sin ETA Rappi** y **una sola zona** en el dataset.
- **Impacto:** El equipo no puede defender **SLA competitivo** ni **variación por colonia** con este dataset: decisiones de **ops y expansión** quedan expuestas.
- **Recomendación:** (1) Extender scraper Rappi para **ETA/rango** visible; (2) diseñar **grid mínimo** de 5–10 direcciones (centro, periferia Norte/Sur, NSE proxy); (3) si hay múltiples corridas, serie temporal en dashboard (bonus rúbrica).

---

## 4. Visualizaciones incluidas

| # | Tipo | Qué muestra |
|---|------|-------------|
| 1 | **Barras agrupadas** | Precio Rappi vs Uber por ítem |
| 2 | **Barras horizontales** | Delta % (Rappi vs Uber) |
| 3 | **Barras** | Delivery fee Rappi vs Uber |
| 4 | **Tabla con codificación de color** | Brecha % por producto (lectura tipo heatmap) |

**Archivo:** `docs/dashboard-insights.html` — regenerar con `npm run report` tras nuevos scrapes.

---

## 5. Próximos pasos sugeridos

1. Añadir **ETA** y **service fee** al pipeline de ambos lados o **carrito controlado**.  
2. **Replicar geografías** para hablar de variabilidad territorial con evidencia.  
3. Repetir **semanal** para **tendencia** (bonus rúbrica).  
4. Exportar este informe + HTML impreso a **PDF único** para entregas académicas o comités.

---

*Documento generado como plantilla analítica; las cifras concretas reflejan `docs/insights-metrics.json` en el momento de `npm run report`.*
