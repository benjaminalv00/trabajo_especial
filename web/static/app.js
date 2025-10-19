const state = {
  defaults: {
    tipo_imagen: "MCMI",
    satelite: "GOES16",
    data_dir: "data/",
    recorte: "[-18.6, -56.45, -79.79, -50.0]",
    export: {
      out_dir: "salidas/",
      show: false,
      shapefile_provincias: "",
    },
  },
  jobs: [],
};

const els = {};
const runState = {
  timer: null,
  lastUpdate: null,
};

function clearRunTimer() {
  if (runState.timer) {
    clearInterval(runState.timer);
    runState.timer = null;
  }
}

function updateRunIndicatorLabel() {
  if (!els.runIndicatorText) return;
  if (!runState.lastUpdate) {
    els.runIndicatorText.textContent = "Procesando…";
    return;
  }
  const diffMs = Date.now() - runState.lastUpdate.getTime();
  const diffSec = Math.max(0, Math.floor(diffMs / 1000));
  const timestamp = runState.lastUpdate.toLocaleTimeString("es-ES", {
    hour12: false,
  });
  const freshness = diffSec === 0 ? "hace instantes" : `hace ${diffSec}s`;
  els.runIndicatorText.textContent = `Procesando… (último log ${timestamp}, ${freshness})`;
}

function setRunning(isRunning) {
  if (!els.runIndicator) return;
  if (isRunning) {
    els.runIndicator.classList.remove("hidden");
    runState.lastUpdate = new Date();
    updateRunIndicatorLabel();
    clearRunTimer();
    runState.timer = setInterval(updateRunIndicatorLabel, 1000);
  } else {
    clearRunTimer();
    els.runIndicator.classList.add("hidden");
    runState.lastUpdate = null;
  }
}

function touchRunIndicator() {
  runState.lastUpdate = new Date();
  updateRunIndicatorLabel();
}

function createEmptyJob() {
  return {
    nombre: "",
    tipo_imagen: "",
    satelite: "",
    datetime: "",
    productos: "true_color",
    canales: "",
    salidas: "PNG",
    data_dir: "",
    recorte: "",
    geotiff: {
      enabled: false,
      producto: "",
      out_dir: "",
      filename_pattern: "{producto}_{ts}.tif",
    },
  };
}

function resetState() {
  state.defaults = {
    tipo_imagen: "MCMI",
    satelite: "GOES16",
    data_dir: "data/",
    recorte: "[-18.6, -56.45, -79.79, -50.0]",
    export: {
      out_dir: "salidas/",
      show: false,
      shapefile_provincias: "",
    },
  };
  state.jobs = [createEmptyJob()];
}

function cacheElements() {
  els.configSelect = document.getElementById("config-select");
  els.loadConfig = document.getElementById("load-config");
  els.newConfig = document.getElementById("new-config");
  els.fileName = document.getElementById("file-name");

  els.defaultTipo = document.getElementById("default-tipo");
  els.defaultSat = document.getElementById("default-sat");
  els.defaultData = document.getElementById("default-data");
  els.defaultRecorte = document.getElementById("default-recorte");
  els.defaultExportOut = document.getElementById("default-export-out");
  els.defaultExportShow = document.getElementById("default-export-show");
  els.defaultExportShp = document.getElementById("default-export-shp");

  els.jobsContainer = document.getElementById("jobs-container");
  els.addJob = document.getElementById("add-job");

  els.yamlOutput = document.getElementById("yaml-output");
  els.logs = document.getElementById("logs");
  els.status = document.getElementById("status");
  els.runIndicator = document.getElementById("run-indicator");
  els.runIndicatorText = document.getElementById("run-indicator-text");

  els.preview = document.getElementById("preview-btn");
  els.save = document.getElementById("save-btn");
  els.run = document.getElementById("run-btn");
}

function setStatus(message, ok = true) {
  els.status.textContent = message;
  els.status.style.color = ok ? "#9be7ff" : "#ff8a80";
}

function toggleBusy(isBusy) {
  [els.preview, els.save, els.run, els.addJob, els.loadConfig, els.newConfig].forEach((btn) => {
    if (btn) btn.disabled = isBusy;
  });
}

function formatRecorteForInput(value) {
  if (Array.isArray(value)) {
    if (!value.length) return "";
    return `[${value.join(", ")}]`;
  }
  if (value === undefined || value === null) return "";
  return String(value);
}

function normalizeRecorteValue(value) {
  if (value === undefined || value === null) return undefined;
  if (Array.isArray(value)) {
    const numbers = value.map((item) => Number(item));
    if (numbers.every((num) => Number.isFinite(num))) {
      return numbers;
    }
    return value;
  }
  const trimmed = String(value).trim();
  if (!trimmed) return undefined;
  const normalized = trimmed.replace(/^[\[]|[\]]$/g, "");
  const parts = normalized
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  if (parts.length === 4) {
    const numbers = parts.map((item) => Number(item));
    if (numbers.every((num) => Number.isFinite(num))) {
      return numbers;
    }
  }
  return trimmed;
}

function formatDatetimeForYaml(value) {
  if (!value) return undefined;
  const trimmed = String(value).trim();
  if (!trimmed) return undefined;
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(trimmed)) {
    return `${trimmed}:00`;
  }
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(trimmed)) {
    return trimmed;
  }
  return trimmed;
}

function formatDatetimeForInput(value) {
  if (!value) return "";
  const str = String(value).trim();
  if (!str) return "";
  const match = str.match(/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})(?::\d{2})?$/);
  if (match) {
    return match[1];
  }
  return str;
}

function renderDefaults() {
  const defaults = state.defaults;
  els.defaultTipo.value = defaults.tipo_imagen || "MCMI";
  els.defaultSat.value = defaults.satelite || "";
  els.defaultData.value = defaults.data_dir || "";
  els.defaultRecorte.value = defaults.recorte || "";
  els.defaultExportOut.value = defaults.export?.out_dir || "";
  els.defaultExportShow.checked = Boolean(defaults.export?.show);
  els.defaultExportShp.value = defaults.export?.shapefile_provincias || "";
}

function escapeHtml(value) {
  const str = value == null ? "" : String(value);
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderJobs() {
  const cards = state.jobs
    .map((job, index) => {
      const geotiffEnabled = job.geotiff?.enabled ? "checked" : "";
      return `
        <article class="job-card" data-index="${index}">
          <header>
            <h3>Job ${index + 1}</h3>
            <button type="button" class="secondary" data-action="remove-job" data-index="${index}">Eliminar</button>
          </header>
          <div class="field-grid">
            <label>Nombre
              <input type="text" data-field="nombre" data-index="${index}" value="${escapeHtml(job.nombre ?? "")}" />
            </label>
            <label>Tipo de imagen
              <input type="text" data-field="tipo_imagen" data-index="${index}" placeholder="(opcional)" value="${escapeHtml(job.tipo_imagen ?? "")}" />
            </label>
            <label>Satélite
              <input type="text" data-field="satelite" data-index="${index}" placeholder="GOES16" value="${escapeHtml(job.satelite ?? "")}" />
            </label>
            <label>Fecha (UTC)
              <input type="datetime-local" data-field="datetime" data-index="${index}" value="${escapeHtml(job.datetime ?? "")}" />
            </label>
            <label>Productos (coma)
              <input type="text" data-field="productos" data-index="${index}" value="${escapeHtml(job.productos ?? "")}" />
            </label>
            <label>Canales (coma)
              <input type="text" data-field="canales" data-index="${index}" value="${escapeHtml(job.canales ?? "")}" />
            </label>
            <label>Salidas (coma)
              <input type="text" data-field="salidas" data-index="${index}" value="${escapeHtml(job.salidas ?? "")}" />
            </label>
            <label>Data dir (opcional)
              <input type="text" data-field="data_dir" data-index="${index}" value="${escapeHtml(job.data_dir ?? "")}" />
            </label>
            <label>Recorte (latN, latS, lonW, lonE)
              <input type="text" data-field="recorte" data-index="${index}" value="${escapeHtml(job.recorte ?? "")}" />
            </label>
          </div>
          <details ${geotiffEnabled ? "open" : ""}>
            <summary>
              <label class="checkbox">
                <input type="checkbox" data-field="geotiff.enabled" data-index="${index}" ${geotiffEnabled} />
                Exportar GeoTIFF
              </label>
            </summary>
            <div class="field-grid">
              <label>Producto
                <input type="text" data-field="geotiff.producto" data-index="${index}" value="${escapeHtml(job.geotiff?.producto ?? "")}" />
              </label>
              <label>Out dir
                <input type="text" data-field="geotiff.out_dir" data-index="${index}" value="${escapeHtml(job.geotiff?.out_dir ?? "")}" />
              </label>
              <label>Filename pattern
                <input type="text" data-field="geotiff.filename_pattern" data-index="${index}" value="${escapeHtml(job.geotiff?.filename_pattern ?? "")}" />
              </label>
            </div>
          </details>
        </article>
      `;
    })
    .join("\n");

  els.jobsContainer.innerHTML = cards;
}

function handleJobInput(event) {
  const target = event.target;
  const index = Number(target.dataset.index);
  const field = target.dataset.field;
  if (Number.isNaN(index) || !field) return;

  const value = target.type === "checkbox" ? target.checked : target.value;

  if (field.startsWith("geotiff.")) {
    const key = field.split(".")[1];
    if (!state.jobs[index].geotiff) state.jobs[index].geotiff = { enabled: false };
    state.jobs[index].geotiff[key] = value;
  } else {
    state.jobs[index][field] = value;
  }
}

function handleJobClick(event) {
  const btn = event.target.closest("button[data-action]");
  if (!btn) return;
  const index = Number(btn.dataset.index);
  if (btn.dataset.action === "remove-job" && !Number.isNaN(index)) {
    state.jobs.splice(index, 1);
    if (state.jobs.length === 0) {
      state.jobs.push(createEmptyJob());
    }
    renderJobs();
  }
}

function bindEvents() {
  els.loadConfig.addEventListener("click", async () => {
    const selected = els.configSelect.value;
    if (!selected) {
      setStatus("Seleccioná un archivo a cargar.", false);
      return;
    }
    try {
      await loadConfig(selected);
      els.fileName.value = selected;
      setStatus(`Configuración ${selected} cargada.`);
    } catch (error) {
      console.error(error);
      setStatus(`Error al cargar: ${error.message}`, false);
    }
  });

  els.newConfig.addEventListener("click", () => {
    resetState();
    renderDefaults();
    renderJobs();
    els.fileName.value = "";
    els.yamlOutput.value = "";
    els.logs.textContent = "Sin ejecutar.";
    setStatus("Configuración nueva lista.");
  });

  [
    [els.defaultTipo, (value) => (state.defaults.tipo_imagen = value)],
    [els.defaultSat, (value) => (state.defaults.satelite = value)],
    [els.defaultData, (value) => (state.defaults.data_dir = value)],
    [els.defaultRecorte, (value) => (state.defaults.recorte = value)],
    [els.defaultExportOut, (value) => {
      if (!state.defaults.export) state.defaults.export = {};
      state.defaults.export.out_dir = value;
    }],
    [els.defaultExportShow, (value) => {
      if (!state.defaults.export) state.defaults.export = {};
      state.defaults.export.show = value;
    }, true],
    [els.defaultExportShp, (value) => {
      if (!state.defaults.export) state.defaults.export = {};
      state.defaults.export.shapefile_provincias = value;
    }],
  ].forEach(([el, handler, isCheckbox]) => {
    if (!el) return;
    const eventName = isCheckbox ? "change" : "input";
    el.addEventListener(eventName, (evt) => handler(isCheckbox ? evt.target.checked : evt.target.value));
  });

  els.addJob.addEventListener("click", () => {
    state.jobs.push(createEmptyJob());
    renderJobs();
    setStatus("Job agregado.");
  });

  els.jobsContainer.addEventListener("input", handleJobInput);
  els.jobsContainer.addEventListener("change", handleJobInput);
  els.jobsContainer.addEventListener("click", handleJobClick);

  els.preview.addEventListener("click", () => {
    try {
      els.yamlOutput.value = buildYaml();
      setStatus("YAML actualizado.");
    } catch (error) {
      console.error(error);
      setStatus(error.message, false);
    }
  });

  els.save.addEventListener("click", async () => {
    const fileName = (els.fileName.value || "").trim();
    if (!fileName) {
      setStatus("Especificá un nombre de archivo.", false);
      return;
    }
    try {
      toggleBusy(true);
      const yamlContent = buildYaml();
      await saveConfig(fileName, yamlContent);
      setStatus(`Guardado como ${fileName}.`);
      await refreshConfigList(fileName);
    } catch (error) {
      console.error(error);
      setStatus(`Error al guardar: ${error.message}`, false);
    } finally {
      toggleBusy(false);
    }
  });

  els.run.addEventListener("click", async () => {
    const fileName = (els.fileName.value || "").trim();
    if (!fileName) {
      setStatus("Especificá un nombre de archivo.", false);
      return;
    }
    try {
      toggleBusy(true);
      setRunning(true);
      setStatus("Generando imágenes, por favor esperá...");
      const yamlContent = buildYaml();
      els.logs.textContent = "";
      const append = (chunk) => {
        els.logs.textContent += chunk;
        els.logs.scrollTop = els.logs.scrollHeight;
        touchRunIndicator();
      };
      const fullLog = await runConfigStream(fileName, yamlContent, append);
      if (fullLog && fullLog.trim()) {
        els.logs.textContent = fullLog;
        els.logs.scrollTop = els.logs.scrollHeight;
      }
      setStatus(`Proceso terminado. Guardado como ${fileName}.`);
      await refreshConfigList(fileName);
    } catch (error) {
      console.error(error);
      if (!els.logs.textContent) {
        els.logs.textContent = error.logs || error.message;
      }
      setStatus(`Error al ejecutar: ${error.message}`, false);
    } finally {
      toggleBusy(false);
      setRunning(false);
    }
  });
}

function splitList(value) {
  if (!value || typeof value !== "string") return [];
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatNumberForRecorte(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) {
    return String(value);
  }
  if (Number.isInteger(num)) {
    return num.toFixed(1);
  }
  return String(num);
}

function formatRecorteInline(recorte) {
  if (!Array.isArray(recorte) || recorte.length !== 4) return null;
  const parts = recorte.map((value) => formatNumberForRecorte(value));
  return `[${parts.join(", ")}]`;
}

function applyInlineRecortes(yamlText, recorteValues) {
  if (!recorteValues.length) return yamlText;
  let index = 0;
  return yamlText.replace(/(^\s*recorte:\s*\n)(?:\s*-\s*[^\n]+\n){4}/gm, (match, prefix) => {
    const inline = recorteValues[index++];
    if (!inline) return match;
    const indent = prefix.match(/^\s*/)?.[0] ?? "";
    return `${indent}recorte: ${inline}\n`;
  });
}

function applyDatetimeFormatting(yamlText, datetimeValues) {
  if (!datetimeValues.length) return yamlText;
  let index = 0;
  return yamlText.replace(/(^\s*datetime:)\s*[^\n]+/gm, (match, label) => {
    const value = datetimeValues[index++];
    if (!value) return match;
    const indent = label.match(/^\s*/)?.[0] ?? "";
    return `${indent}datetime: ${value}`;
  });
}

function buildDefaults() {
  const defaults = {
    tipo_imagen: state.defaults.tipo_imagen || undefined,
    satelite: state.defaults.satelite || undefined,
    data_dir: state.defaults.data_dir || undefined,
  };

  const recorteValue = normalizeRecorteValue(state.defaults.recorte);
  if (recorteValue !== undefined) {
    defaults.recorte = recorteValue;
  }

  const exportCfg = {};
  if (state.defaults.export?.out_dir) {
    exportCfg.out_dir = state.defaults.export.out_dir;
  }
  if (typeof state.defaults.export?.show === "boolean") {
    exportCfg.show = state.defaults.export.show;
  }
  if (state.defaults.export?.shapefile_provincias) {
    exportCfg.shapefile_provincias = state.defaults.export.shapefile_provincias;
  }

  if (Object.keys(exportCfg).length) {
    defaults.export = exportCfg;
  }

  return cleanObject(defaults);
}

function buildJob(job) {
  const jobCfg = {
    nombre: job.nombre || undefined,
    tipo_imagen: job.tipo_imagen || undefined,
    satelite: job.satelite || undefined,
    data_dir: job.data_dir || undefined,
  };

  const datetimeValue = formatDatetimeForYaml(job.datetime);
  if (datetimeValue) {
    jobCfg.datetime = datetimeValue;
  }

  const productos = splitList(job.productos);
  if (productos.length) jobCfg.productos = productos;

  const canales = splitList(job.canales);
  if (canales.length) jobCfg.canales = canales;

  const salidas = splitList(job.salidas);
  if (salidas.length) jobCfg.salidas = salidas;

  const recorteValue = normalizeRecorteValue(job.recorte);
  if (recorteValue !== undefined) {
    jobCfg.recorte = recorteValue;
  }

  if (job.geotiff?.enabled) {
    const geotiff = {};
    if (job.geotiff.producto) geotiff.producto = job.geotiff.producto;
    if (job.geotiff.out_dir) geotiff.out_dir = job.geotiff.out_dir;
    if (job.geotiff.filename_pattern) geotiff.filename_pattern = job.geotiff.filename_pattern;
    if (Object.keys(geotiff).length) {
      jobCfg.geotiff_conf = geotiff;
    }
  }

  return cleanObject(jobCfg);
}

function cleanObject(value) {
  if (Array.isArray(value)) {
    const cleaned = value
      .map((item) => cleanObject(item))
      .filter((item) => item !== undefined && !(Array.isArray(item) && item.length === 0));
    return cleaned.length ? cleaned : undefined;
  }
  if (value && typeof value === "object") {
    const result = {};
    Object.entries(value).forEach(([key, val]) => {
      const cleanVal = cleanObject(val);
      if (
        cleanVal !== undefined &&
        !(
          typeof cleanVal === "string" && cleanVal.trim() === ""
        ) &&
        !(
          Array.isArray(cleanVal) && cleanVal.length === 0
        ) &&
        !(typeof cleanVal === "object" && Object.keys(cleanVal).length === 0)
      ) {
        result[key] = cleanVal;
      }
    });
    return Object.keys(result).length ? result : undefined;
  }
  return value;
}

function buildYaml() {
  const jobs = state.jobs.map((job) => buildJob(job)).filter(Boolean);
  if (jobs.length === 0) {
    throw new Error("Necesitás al menos un job para generar YAML.");
  }
  const defaults = buildDefaults();
  if (!defaults) {
    throw new Error("Revisá los defaults ingresados.");
  }
  const doc = cleanObject({ defaults, jobs });
  if (!doc) {
    throw new Error("Configuración vacía.");
  }
  const recorteValues = [];
  if (Array.isArray(doc?.defaults?.recorte)) {
    const formatted = formatRecorteInline(doc.defaults.recorte);
    if (formatted) recorteValues.push(formatted);
  }
  if (Array.isArray(doc?.jobs)) {
    doc.jobs.forEach((job) => {
      if (Array.isArray(job?.recorte)) {
        const formatted = formatRecorteInline(job.recorte);
        if (formatted) recorteValues.push(formatted);
      }
    });
  }

  const datetimeValues = Array.isArray(doc?.jobs)
    ? doc.jobs.map((job) => (typeof job?.datetime === "string" ? job.datetime : null)).filter(Boolean)
    : [];

  let yamlText = window.jsyaml.dump(doc, {
    lineWidth: 120,
    noRefs: true,
    flowLevel: 1,
  });

  yamlText = applyInlineRecortes(yamlText, recorteValues);
  yamlText = applyDatetimeFormatting(yamlText, datetimeValues);
  return yamlText;
}

async function saveConfig(name, content) {
  const response = await fetch("/api/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, content }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "No se pudo guardar la configuración.");
  }
  return response.json();
}

async function runConfigStream(name, content, onChunk) {
  const response = await fetch("/api/run-stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, content, save: true }),
  });

  if (!response.ok) {
    const contentType = response.headers.get("content-type") || "";
    let detail = "Falló la ejecución";
    if (contentType.includes("application/json")) {
      const data = await response.json().catch(() => ({}));
      detail = data.detail || detail;
    } else {
      detail = (await response.text().catch(() => "")) || detail;
    }
    throw new Error(detail.trim());
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("No se pudo leer la respuesta del servidor.");
  }

  const decoder = new TextDecoder();
  let output = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });
    if (chunk) {
      output += chunk;
      if (onChunk) onChunk(chunk);
    }
  }

  const tail = decoder.decode();
  if (tail) {
    output += tail;
    if (onChunk) onChunk(tail);
  }

  return output;
}

async function refreshConfigList(selectName) {
  const response = await fetch("/api/configs");
  if (!response.ok) throw new Error("No se pudo obtener la lista de configuraciones.");
  const data = await response.json();
  populateConfigSelect(data.configs || [], selectName);
}

async function loadConfig(name) {
  const response = await fetch(`/api/configs/${encodeURIComponent(name)}`);
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "No se pudo cargar el archivo.");
  }
  const data = await response.json();
  const parsed = window.jsyaml.load(data.content) || {};
  resetState();

  if (parsed.defaults) {
    state.defaults.tipo_imagen = parsed.defaults.tipo_imagen || state.defaults.tipo_imagen;
    state.defaults.satelite = parsed.defaults.satelite || "";
    state.defaults.data_dir = parsed.defaults.data_dir || "";
    state.defaults.recorte = formatRecorteForInput(parsed.defaults.recorte);
    if (parsed.defaults.export) {
      state.defaults.export.out_dir = parsed.defaults.export.out_dir || "";
      state.defaults.export.show = Boolean(parsed.defaults.export.show);
      state.defaults.export.shapefile_provincias = parsed.defaults.export.shapefile_provincias || "";
    }
  }

  if (Array.isArray(parsed.jobs) && parsed.jobs.length) {
    state.jobs = parsed.jobs.map((job) => {
      const jobState = createEmptyJob();
      jobState.nombre = job.nombre || "";
      jobState.tipo_imagen = job.tipo_imagen || "";
      jobState.satelite = job.satelite || "";
      jobState.datetime = formatDatetimeForInput(job.datetime);
      jobState.productos = Array.isArray(job.productos) ? job.productos.join(", ") : job.productos || "";
      jobState.canales = Array.isArray(job.canales) ? job.canales.join(", ") : job.canales || "";
      jobState.salidas = Array.isArray(job.salidas) ? job.salidas.join(", ") : job.salidas || "";
      jobState.data_dir = job.data_dir || "";
      jobState.recorte = formatRecorteForInput(job.recorte);
      const geotiffConf = job.geotiff_conf || job.geotiff;
      if (geotiffConf) {
        jobState.geotiff.enabled = true;
        jobState.geotiff.producto = geotiffConf.producto || "";
        jobState.geotiff.out_dir = geotiffConf.out_dir || "";
        jobState.geotiff.filename_pattern = geotiffConf.filename_pattern || jobState.geotiff.filename_pattern;
      }
      return jobState;
    });
  }

  renderDefaults();
  renderJobs();
}

function populateConfigSelect(configs, selected) {
  els.configSelect.innerHTML = `<option value="">-- elegir --</option>`;
  configs.forEach((name) => {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    if (selected && selected === name) option.selected = true;
    els.configSelect.append(option);
  });
}

async function init() {
  cacheElements();
  resetState();
  renderDefaults();
  renderJobs();
  bindEvents();
  setRunning(false);
  try {
    await refreshConfigList();
    setStatus("Listo.");
  } catch (error) {
    console.error(error);
    setStatus(`No se pudo cargar la lista inicial: ${error.message}`, false);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
