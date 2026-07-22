const state = {
  files: [],
  inspection: null,
  result: null,
};

const mappingLabels = {
  producto: "Producto",
  proveedor: "Proveedor",
  cantidad: "Cantidad",
  importe: "Importe de venta",
  compra: "Precio de compra",
  venta: "Precio de venta",
  envio: "Envío del proveedor",
  stock: "Stock",
  peso: "Peso / gramaje",
  largo: "Largo",
  ancho: "Ancho",
  alto: "Alto",
};

const mappingFormNames = {
  producto: "columna_producto",
  proveedor: "columna_proveedor",
  cantidad: "columna_cantidad",
  importe: "columna_importe",
  compra: "columna_compra",
  venta: "columna_venta",
  envio: "columna_envio",
  peso: "columna_peso",
  stock: "columna_stock",
  largo: "columna_largo",
  ancho: "columna_ancho",
  alto: "columna_alto",
};

const $ = (id) => document.getElementById(id);

const fileInput = $("fileInput");
const inspectButton = $("inspectButton");
const analyzeButton = $("analyzeButton");
const inspectionSection = $("inspectionSection");
const settingsSection = $("settingsSection");
const resultsSection = $("resultsSection");
const loading = $("loading");
const message = $("message");

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function showLoading(text) {
  $("loadingText").textContent = text;
  loading.classList.remove("hidden");
}

function hideLoading() {
  loading.classList.add("hidden");
}

let messageTimer;
function showMessage(text) {
  clearTimeout(messageTimer);
  message.textContent = text;
  message.classList.remove("hidden");
  messageTimer = setTimeout(() => message.classList.add("hidden"), 7000);
}

function money(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "No disponible";
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    maximumFractionDigits: 2,
  }).format(number);
}

function number(value, digits = 2) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return String(value ?? "—");
  return new Intl.NumberFormat("es-MX", { maximumFractionDigits: digits }).format(parsed);
}

function setFiles(files) {
  state.files = Array.from(files).filter((file) => /\.(csv|xlsx|xls)$/i.test(file.name));
  state.inspection = null;
  state.result = null;
  inspectButton.disabled = state.files.length === 0;
  inspectionSection.classList.add("hidden");
  settingsSection.classList.add("hidden");
  resultsSection.classList.add("hidden");

  const list = $("fileList");
  list.replaceChildren();
  for (const file of state.files) {
    const chip = document.createElement("span");
    chip.className = "file-chip";
    chip.textContent = `${file.name} · ${(file.size / 1024).toFixed(1)} KB`;
    list.append(chip);
  }
}

function appendFiles(formData) {
  for (const file of state.files) {
    formData.append("files", file, file.name);
  }
}

async function requestJson(url, options) {
  const response = await fetch(url, options);
  let payload;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (!response.ok) {
    const detail = payload?.detail;
    throw new Error(typeof detail === "string" ? detail : "No se pudo completar la solicitud.");
  }
  return payload;
}

function createStat(label, value) {
  const card = document.createElement("div");
  card.className = "mini-stat";
  const title = document.createElement("span");
  title.textContent = label;
  const strong = document.createElement("strong");
  strong.textContent = value;
  card.append(title, strong);
  return card;
}

function renderTable(container, rows, preferredColumns = null) {
  container.replaceChildren();
  if (!rows?.length) {
    const empty = document.createElement("p");
    empty.style.padding = "16px";
    empty.style.color = "#63777a";
    empty.textContent = "No hay una tabla disponible con las columnas actuales.";
    container.append(empty);
    return;
  }

  const allColumns = [...new Set(rows.flatMap((row) => Object.keys(row)))];
  const columns = preferredColumns
    ? preferredColumns.filter((column) => allColumns.includes(column))
    : allColumns;
  const table = document.createElement("table");
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  for (const column of columns) {
    const th = document.createElement("th");
    th.textContent = column;
    headerRow.append(th);
  }
  thead.append(headerRow);

  const tbody = document.createElement("tbody");
  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const column of columns) {
      const td = document.createElement("td");
      const value = row[column];
      if (typeof value === "number" && /precio|costo|envío|envio|venta|iva|utilidad|importe|ganancia/i.test(column)) {
        td.textContent = money(value);
      } else if (typeof value === "number") {
        td.textContent = number(value);
      } else {
        td.textContent = value ?? "—";
      }
      tr.append(td);
    }
    tbody.append(tr);
  }
  table.append(thead, tbody);
  container.append(table);
}

function renderInspection(data) {
  state.inspection = data;
  inspectionSection.classList.remove("hidden");
  settingsSection.classList.remove("hidden");
  resultsSection.classList.add("hidden");

  const stats = $("inspectionStats");
  stats.replaceChildren(
    createStat("Registros cargados", number(data.rows, 0)),
    createStat("Columnas detectadas", number(data.columns.length, 0)),
    createStat("Filas limpias", number(data.cleaning.filas_finales, 0)),
    createStat("Duplicados eliminados", number(data.cleaning.duplicados_eliminados, 0)),
  );

  const detectedList = $("detectedList");
  detectedList.replaceChildren();
  for (const [concept, label] of Object.entries(mappingLabels)) {
    const tag = document.createElement("span");
    const detected = data.detected[concept];
    tag.className = `detected-tag${detected ? "" : " missing"}`;
    tag.textContent = `${label}: ${detected || "no detectada"}`;
    detectedList.append(tag);
  }

  const grid = $("mappingGrid");
  grid.replaceChildren();
  for (const [concept, labelText] of Object.entries(mappingLabels)) {
    const label = document.createElement("label");
    label.className = "field";
    const title = document.createElement("span");
    title.textContent = labelText;
    const select = document.createElement("select");
    select.dataset.mapping = concept;
    const none = document.createElement("option");
    none.value = "";
    none.textContent = "— No seleccionar —";
    select.append(none);
    for (const column of data.columns) {
      const option = document.createElement("option");
      option.value = column;
      option.textContent = column;
      option.selected = data.detected[concept] === column;
      select.append(option);
    }
    select.addEventListener("change", () => {
      updateProductsFromPreview();
      updateConditionalFields();
    });
    label.append(title, select);
    grid.append(label);
  }

  renderTable($("previewTable"), data.preview);
  updateProductOptions(data.products);
  updateConditionalFields();

  const shippingColumn = data.detected.envio || "";
  $("shippingType").value = /pedido/i.test(shippingColumn) ? "por_pedido" : "por_unidad";
  inspectionSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function getMapping(concept) {
  return document.querySelector(`[data-mapping="${concept}"]`)?.value || "";
}

function updateProductsFromPreview() {
  const productColumn = getMapping("producto");
  if (!productColumn || !state.inspection) {
    updateProductOptions([]);
    return;
  }
  const products = [...new Set(state.inspection.preview.map((row) => row[productColumn]).filter(Boolean))]
    .sort((a, b) => String(a).localeCompare(String(b), "es"));
  updateProductOptions(products);
}

function updateProductOptions(products) {
  const select = $("productSelect");
  const previous = select.value;
  select.replaceChildren();
  if (!products?.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No hay productos detectados";
    select.append(option);
    return;
  }
  for (const product of products) {
    const option = document.createElement("option");
    option.value = product;
    option.textContent = product;
    select.append(option);
  }
  if (products.map(String).includes(previous)) select.value = previous;
}

function updateConditionalFields() {
  const hasWeight = Boolean(getMapping("peso"));
  $("manualWeightField").classList.toggle("hidden", hasWeight);
}

async function inspectFiles() {
  if (!state.files.length) return;
  showLoading("Leyendo columnas y limpiando datos…");
  try {
    const formData = new FormData();
    appendFiles(formData);
    const data = await requestJson("/api/inspect", { method: "POST", body: formData });
    renderInspection(data);
  } catch (error) {
    showMessage(error.message);
  } finally {
    hideLoading();
  }
}

function valueOf(id) {
  return $(id).value;
}

function buildAnalysisForm() {
  const formData = new FormData();
  appendFiles(formData);
  formData.append("producto", valueOf("productSelect"));
  for (const [concept, fieldName] of Object.entries(mappingFormNames)) {
    formData.append(fieldName, getMapping(concept));
  }
  const values = {
    tipo_envio: valueOf("shippingType"),
    unidad_peso: valueOf("weightUnit"),
    unidad_dimensiones: valueOf("dimensionUnit"),
    numero_unidades: valueOf("unitsInput"),
    peso_manual: valueOf("manualWeightInput"),
    tarifa_estandar: valueOf("standardShipping"),
    tarifa_ltl: valueOf("ltlShipping"),
    envio_cliente: valueOf("customerShipping"),
    comision: valueOf("commission"),
    promocion: valueOf("promotion"),
    margen: valueOf("margin"),
    iva: valueOf("vat"),
    costo_m3: valueOf("volumeCost"),
    variacion_compra: valueOf("purchaseVariation"),
    variacion_logistica: valueOf("logisticsVariation"),
    iteraciones: valueOf("iterations"),
  };
  for (const [name, value] of Object.entries(values)) formData.append(name, value);
  return formData;
}

function createMetric(label, value, note = "") {
  const card = document.createElement("div");
  card.className = "metric";
  const labelNode = document.createElement("span");
  labelNode.textContent = label;
  const strong = document.createElement("strong");
  strong.textContent = value;
  card.append(labelNode, strong);
  if (note) {
    const small = document.createElement("small");
    small.textContent = note;
    card.append(small);
  }
  return card;
}

function findKey(row, fragment) {
  return row ? Object.keys(row).find((key) => key.includes(fragment)) : undefined;
}

function renderBarChart(container, rows, labelColumn, valueColumn, formatter, maximum = null) {
  container.replaceChildren();
  if (!rows?.length || !labelColumn || !valueColumn) return;
  const max = maximum ?? Math.max(...rows.map((row) => Number(row[valueColumn]) || 0), 1);
  for (const row of rows) {
    const value = Number(row[valueColumn]) || 0;
    const line = document.createElement("div");
    line.className = "bar-row";
    const label = document.createElement("strong");
    label.textContent = row[labelColumn] ?? "Proveedor";
    const track = document.createElement("div");
    track.className = "bar-track";
    const fill = document.createElement("div");
    fill.className = "bar-fill";
    fill.style.width = `${Math.min(100, Math.max(1, (value / max) * 100))}%`;
    track.append(fill);
    const shown = document.createElement("span");
    shown.className = "bar-value";
    shown.textContent = formatter(value);
    line.append(label, track, shown);
    container.append(line);
  }
}

function filteredQuotes() {
  const quotes = state.result?.tables?.cotizacion_proveedores || [];
  const providerColumn = state.result?.selected_columns?.proveedor;
  const filter = $("providerFilter").value;
  return filter && providerColumn
    ? quotes.filter((row) => String(row[providerColumn]) === filter)
    : quotes;
}

function renderQuoteComparison() {
  if (!state.result) return;
  const quotes = filteredQuotes();
  const providerColumn = state.result.selected_columns.proveedor;
  const preferred = [
    providerColumn,
    "Tipo logístico calculado",
    "Precio de compra promedio",
    "Costo de envío interno total",
    "Precio de venta con IVA",
    "Envío total sumado",
    "Total venta + envío con IVA",
    "Precio por unidad con IVA",
    "Stock disponible",
  ];
  renderTable($("quoteTable"), quotes, preferred);
  renderBarChart(
    $("priceChart"),
    quotes,
    providerColumn,
    "Total venta + envío con IVA",
    money,
  );
}

function renderResult(data) {
  state.result = data;
  resultsSection.classList.remove("hidden");
  const recommendation = data.recommendation;
  $("confidenceBadge").textContent = `Confianza ${recommendation.confianza}`;
  $("recommendationCard").innerHTML = recommendation.proveedor
    ? `<span class="label">RECOMENDACIÓN CON LOS DATOS DISPONIBLES</span>
       <h3>${escapeHtml(recommendation.proveedor)}</h3>
       <p>Se seleccionó por ${escapeHtml(recommendation.criterio)}.${
         recommendation.provisional
           ? ` Es provisional porque faltan: ${escapeHtml((recommendation.faltantes || []).join(", ") || "datos complementarios")}.`
           : " La información principal está completa."
       }</p>`
    : `<span class="label">RECOMENDACIÓN PENDIENTE</span>
       <h3>Faltan datos</h3><p>${escapeHtml(recommendation.criterio)}</p>`;

  const quotes = data.tables.cotizacion_proveedores || [];
  const providerColumn = data.selected_columns.proveedor;
  const selectedQuote = quotes.find(
    (row) => providerColumn && String(row[providerColumn]) === String(recommendation.proveedor),
  ) || quotes[0] || {};
  const logisticsKey = findKey(selectedQuote, "Tipo logístico");
  const metrics = $("metricGrid");
  metrics.replaceChildren(
    createMetric("Tipo de envío", logisticsKey ? selectedQuote[logisticsKey] : "No disponible", "Según el peso registrado"),
    createMetric("Envío total", money(selectedQuote["Envío total sumado"]), "Logística interna + envío al cliente"),
    createMetric("Venta antes del envío", money(selectedQuote["Precio de venta con IVA"]), "Producto, margen, plataforma e IVA"),
    createMetric("Venta + envío", money(selectedQuote["Total venta + envío con IVA"]), "Total final que pagará el cliente"),
  );

  const providerFilter = $("providerFilter");
  providerFilter.replaceChildren(new Option("Todos", ""));
  const providers = [...new Set(quotes.map((row) => row[providerColumn]).filter(Boolean))];
  for (const provider of providers) providerFilter.add(new Option(provider, provider));
  renderQuoteComparison();

  const monteCarlo = data.tables.monte_carlo_proveedores || [];
  renderTable($("monteCarloTable"), monteCarlo, [
    providerColumn,
    "Probabilidad de ser más económico (%)",
    "Precio total promedio simulado",
    "Escenario favorable (percentil 5)",
    "Escenario desfavorable (percentil 95)",
    "Stock disponible",
  ]);
  renderBarChart(
    $("monteCarloChart"),
    monteCarlo,
    providerColumn,
    "Probabilidad de ser más económico (%)",
    (value) => `${number(value, 1)}%`,
    100,
  );

  const conclusions = $("conclusionsList");
  conclusions.replaceChildren();
  for (const conclusion of data.conclusions || []) {
    const li = document.createElement("li");
    li.textContent = conclusion;
    conclusions.append(li);
  }
  const warnings = $("warningsList");
  warnings.replaceChildren();
  const warningRows = data.warnings?.length ? data.warnings : ["No se generaron avisos adicionales."];
  for (const warning of warningRows) {
    const li = document.createElement("li");
    li.textContent = warning;
    warnings.append(li);
  }

  resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function analyzeFiles() {
  if (!state.files.length) return;
  showLoading("Comparando proveedores y ejecutando Monte Carlo…");
  analyzeButton.disabled = true;
  try {
    const data = await requestJson("/api/analyze", {
      method: "POST",
      body: buildAnalysisForm(),
    });
    renderResult(data);
  } catch (error) {
    showMessage(error.message);
  } finally {
    analyzeButton.disabled = false;
    hideLoading();
  }
}

function downloadBase64(base64, filename, mimeType) {
  if (!base64) return;
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  const url = URL.createObjectURL(new Blob([bytes], { type: mimeType }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function useDemo() {
  showLoading("Preparando datos de demostración…");
  try {
    const response = await fetch("/datos_demostracion.csv");
    if (!response.ok) throw new Error("No se pudo abrir el archivo de demostración.");
    const blob = await response.blob();
    setFiles([new File([blob], "datos_demostracion.csv", { type: "text/csv" })]);
    await inspectFiles();
  } catch (error) {
    showMessage(error.message);
  } finally {
    hideLoading();
  }
}

fileInput.addEventListener("change", (event) => setFiles(event.target.files));
inspectButton.addEventListener("click", inspectFiles);
analyzeButton.addEventListener("click", analyzeFiles);
$("demoButton").addEventListener("click", useDemo);
$("providerFilter").addEventListener("change", renderQuoteComparison);
$("downloadExcel").addEventListener("click", () =>
  downloadBase64(
    state.result?.downloads?.excel,
    "analisis_proveedores.xlsx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  ),
);
$("downloadCsv").addEventListener("click", () =>
  downloadBase64(state.result?.downloads?.csv, "analisis_proveedores.csv", "text/csv"),
);

const dropzone = $("dropzone");
for (const eventName of ["dragenter", "dragover"]) {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.add("dragging");
  });
}
for (const eventName of ["dragleave", "drop"]) {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.remove("dragging");
  });
}
dropzone.addEventListener("drop", (event) => setFiles(event.dataTransfer.files));
