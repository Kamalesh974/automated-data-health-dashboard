// ---------------------------------------------------------------------------
// Theme
// ---------------------------------------------------------------------------
const themeToggle = document.getElementById("theme-toggle");
const savedTheme = localStorage.getItem("theme");
if (savedTheme) document.documentElement.setAttribute("data-theme", savedTheme);

themeToggle.addEventListener("click", () => {
  const current = document.documentElement.getAttribute("data-theme");
  const isDark = current
    ? current === "dark"
    : window.matchMedia("(prefers-color-scheme: dark)").matches;
  const next = isDark ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("theme", next);
});

// ---------------------------------------------------------------------------
// File selection
// ---------------------------------------------------------------------------
const fileInput = document.getElementById("file-input");
const fileNameEl = document.getElementById("file-name");
const fileDrop = document.querySelector(".file-drop");
const analyzeBtn = document.getElementById("analyze-btn");
const methodSelect = document.getElementById("opt-method");
const kField = document.getElementById("k-field");
const imputeCheckbox = document.getElementById("opt-impute");
const imputeMethodSelect = document.getElementById("opt-impute-method");
const imputeMethodField = document.getElementById("impute-method-field");
const imputeKField = document.getElementById("impute-k-field");
const statusArea = document.getElementById("status-area");
const resultsEl = document.getElementById("results");

function syncImputeFields() {
  const on = imputeCheckbox.checked;
  imputeMethodField.classList.toggle("hidden", !on);
  imputeKField.classList.toggle("hidden", !(on && imputeMethodSelect.value === "knn"));
}
imputeCheckbox.addEventListener("change", syncImputeFields);
imputeMethodSelect.addEventListener("change", syncImputeFields);
syncImputeFields();

let currentFile = null;

function setFile(file) {
  currentFile = file;
  fileNameEl.textContent = file ? `${file.name} (${(file.size / 1024).toFixed(1)} KB)` : "Click to choose a CSV, or drop one here";
  if (file) updatePreview(file);
}

// ---------------------------------------------------------------------------
// Quick preview
// ---------------------------------------------------------------------------
const previewCard = document.getElementById("preview-card");
const previewNote = document.getElementById("preview-note");
const previewChartGrid = document.getElementById("preview-chart-grid");
let previewCharts = [];
let previewToken = 0;

function parseCsvText(text) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; } else { inQuotes = false; }
      } else {
        field += c;
      }
    } else if (c === '"') {
      inQuotes = true;
    } else if (c === ",") {
      row.push(field);
      field = "";
    } else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(field);
      field = "";
      if (row.length > 1 || row[0] !== "") rows.push(row);
      row = [];
    } else {
      field += c;
    }
  }
  if (field !== "" || row.length) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}

const NA_TOKENS = new Set([
  "", "#N/A", "#N/A N/A", "#NA", "-1.#IND", "-1.#QNAN", "-NaN", "-nan",
  "1.#IND", "1.#QNAN", "<NA>", "N/A", "NA", "NULL", "NaN", "None", "n/a", "nan", "null",
]);

function extractNumericColumns(text) {
  const rows = parseCsvText(text);
  if (rows.length < 2) return {};
  const header = rows[0];
  const dataRows = rows.slice(1).filter((r) => r.length === header.length);
  const columns = {};
  header.forEach((name, ci) => {
    const cells = dataRows.map((r) => (r[ci] !== undefined ? r[ci].trim() : ""));
    const informative = cells.filter((v) => !NA_TOKENS.has(v));
    const allNumeric = informative.length > 0 && informative.every((v) => Number.isFinite(Number(v)));
    if (allNumeric) columns[name || `column_${ci}`] = informative.map(Number);
  });
  return columns;
}

function destroyPreviewCharts() {
  previewCharts.forEach((c) => c.destroy());
  previewCharts = [];
}

async function updatePreview(file) {
  const token = ++previewToken;
  try {
    const text = await file.text();
    if (token !== previewToken) return;
    const columns = extractNumericColumns(text);
    const names = Object.keys(columns);
    destroyPreviewCharts();
    previewCard.classList.remove("hidden");

    if (names.length === 0) {
      previewChartGrid.innerHTML = "";
      previewNote.textContent = "No numeric columns detected for a preview.";
      return;
    }

    previewNote.textContent = `${names.length} numeric column(s), computed from the raw file (client-side, quick estimate)`;
    previewChartGrid.innerHTML = names
      .map((n) => `<div class="chart-box"><h4>${n}</h4><canvas id="preview-box-${n.replace(/[^a-zA-Z0-9_-]/g, "_")}"></canvas></div>`)
      .join("");

    names.forEach((n) => {
      const canvas = document.getElementById(`preview-box-${n.replace(/[^a-zA-Z0-9_-]/g, "_")}`);
      previewCharts.push(
        new Chart(canvas, {
          type: "boxplot",
          data: {
            labels: [n],
            datasets: [
              {
                label: n,
                data: [columns[n]],
                backgroundColor: "rgba(2, 128, 144, 0.25)",
                borderColor: "#028090",
                borderWidth: 1.5,
                outlierColor: "#e8524d",
                itemRadius: 2,
              },
            ],
          },
          options: baseChartOptions({ plugins: { legend: { display: false } } }),
        })
      );
    });
  } catch (err) {
    if (token !== previewToken) return;
    previewCard.classList.remove("hidden");
    previewChartGrid.innerHTML = "";
    previewNote.textContent = "Could not preview this file (is it a valid CSV?).";
  }
}

fileInput.addEventListener("change", () => {
  if (fileInput.files.length) setFile(fileInput.files[0]);
});

["dragover", "dragleave", "drop"].forEach((evt) => {
  fileDrop.addEventListener(evt, (e) => {
    e.preventDefault();
    fileDrop.classList.toggle("dragover", evt === "dragover");
  });
});
fileDrop.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file) setFile(file);
});

document.querySelectorAll(".sample-btn").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const name = btn.dataset.sample;
    const resp = await fetch(`/samples/${name}`);
    const blob = await resp.blob();
    setFile(new File([blob], name, { type: "text/csv" }));
  });
});

methodSelect.addEventListener("change", () => {
  kField.style.display = methodSelect.value === "isolation_forest" ? "none" : "flex";
});

function showStatus(kind, message) {
  statusArea.innerHTML = message ? `<div class="status-box status-${kind}">${message}</div>` : "";
}

// ---------------------------------------------------------------------------
// Formatting & Table helpers
// ---------------------------------------------------------------------------
function fmt(v) {
  if (v === null || v === undefined) return "";
  if (typeof v === "number") {
    if (Number.isInteger(v)) return String(v);
    return v.toFixed(Math.abs(v) < 1 ? 4 : 3);
  }
  return String(v);
}

function csvEscape(v) {
  const s = v === null || v === undefined ? "" : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function downloadCsv(filename, columns, rows, showIndex) {
  const header = (showIndex ? [""] : []).concat(columns);
  const lines = [header.map(csvEscape).join(",")];
  rows.forEach((row) => {
    const cells = (showIndex ? [row._index] : []).concat(columns.map((c) => row[c]));
    lines.push(cells.map(csvEscape).join(","));
  });
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

let tableSeq = 0;
const tableState = {};

function compareValues(a, b) {
  const an = a === null || a === undefined;
  const bn = b === null || b === undefined;
  if (an && bn) return 0;
  if (an) return 1;
  if (bn) return -1;
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), undefined, { numeric: true });
}

function renderTableCard(title, table, opts = {}) {
  const id = `tbl${tableSeq++}`;
  const showIndex = opts.showIndex !== false;
  tableState[id] = {
    columns: table && table.columns ? table.columns : [],
    rows: table && table.rows ? table.rows.slice() : [],
    showIndex,
    rowClass: opts.rowClass || null,
    filename: opts.filename || "table.csv",
    sortCol: null,
    sortDir: 1,
  };
  const head = title
    ? `<div class="section-head"><h3>${title}</h3><button type="button" class="small-btn" onclick="exportTable('${id}')">&#8681; Export CSV</button></div>`
    : "";
  return `${head}<div id="${id}"></div>`;
}

function drawTable(id) {
  const state = tableState[id];
  const container = document.getElementById(id);
  if (!state || !container) return;
  if (state.rows.length === 0) {
    container.innerHTML = `<p class="note-line">(none)</p>`;
    return;
  }
  const headCells =
    (state.showIndex ? "<th></th>" : "") +
    state.columns
      .map((c) => {
        const active = state.sortCol === c;
        const arrow = active ? (state.sortDir === 1 ? "&#9650;" : "&#9660;") : "&#8597;";
        return `<th class="sortable${active ? " sort-active" : ""}" onclick="sortTable('${id}','${c}')">${c}<span class="sort-arrow">${arrow}</span></th>`;
      })
      .join("");
  const body = state.rows
    .map((row) => {
      const cls = state.rowClass ? state.rowClass(row) : "";
      const idxCell = state.showIndex ? `<td>${fmt(row._index)}</td>` : "";
      const cells = state.columns.map((c) => `<td>${fmt(row[c])}</td>`).join("");
      return `<tr class="${cls}">${idxCell}${cells}</tr>`;
    })
    .join("");
  container.innerHTML = `<div class="table-wrap"><table><thead><tr>${headCells}</tr></thead><tbody>${body}</tbody></table></div>`;
}

window.sortTable = function (id, col) {
  const state = tableState[id];
  if (!state) return;
  state.sortDir = state.sortCol === col ? -state.sortDir : 1;
  state.sortCol = col;
  state.rows.sort((a, b) => state.sortDir * compareValues(a[col], b[col]));
  drawTable(id);
};

window.exportTable = function (id) {
  const state = tableState[id];
  if (!state) return;
  downloadCsv(state.filename, state.columns, state.rows, state.showIndex);
};

function drawAllTables() {
  Object.keys(tableState).forEach(drawTable);
}

// ---------------------------------------------------------------------------
// Download Cleaned CSV Export
// ---------------------------------------------------------------------------
async function downloadCleanedCSV() {
  if (!currentFile) {
    alert("Please choose or drop a CSV file first.");
    return;
  }

  const formData = new FormData();
  formData.append("file", currentFile);
  formData.append("impute_method", imputeMethodSelect.value);
  formData.append("impute_k", document.getElementById("opt-impute-k").value || 5);

  try {
    const response = await fetch("/api/export", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.error || "Export failed");
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "cleaned_profiled_data.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    alert("Could not generate export: " + err.message);
  }
}

// ---------------------------------------------------------------------------
// Charts & Visualizations
// ---------------------------------------------------------------------------
let activeCharts = [];

function destroyCharts() {
  activeCharts.forEach((c) => c.destroy());
  activeCharts = [];
}

const CHART_COLORS = {
  both: "#e8a33d",
  isolation_forest: "#3d7ce8",
  knn: "#2fbf71",
  none: "#9aa0b0",
};
const CHART_LABELS = { both: "Flagged by both", isolation_forest: "Isolation Forest only", knn: "KNN only", none: "Not flagged" };

function baseChartOptions(extra = {}) {
  const gridColor = getComputedStyle(document.documentElement).getPropertyValue("--border").trim();
  const textColor = getComputedStyle(document.documentElement).getPropertyValue("--muted").trim();
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: textColor } } },
    scales: {
      x: { grid: { color: gridColor }, ticks: { color: textColor } },
      y: { grid: { color: gridColor }, ticks: { color: textColor } },
    },
    ...extra,
  };
}

function buildScatterChart(canvas, raw, flaggedBy, xCol, yCol) {
  const buckets = { both: [], isolation_forest: [], knn: [], none: [] };
  raw.rows.forEach((row) => {
    const x = row[xCol];
    const y = row[yCol];
    if (x === null || y === null || x === undefined || y === undefined) return;
    const status = flaggedBy[String(row._index)] || "none";
    buckets[status].push({ x, y });
  });
  const datasets = Object.keys(buckets)
    .filter((k) => buckets[k].length)
    .map((k) => ({
      label: CHART_LABELS[k],
      data: buckets[k],
      backgroundColor: CHART_COLORS[k],
      pointRadius: k === "none" ? 3 : 5,
      pointHoverRadius: 7,
    }));
  return new Chart(canvas, {
    type: "scatter",
    data: { datasets },
    options: baseChartOptions({
      scales: {
        x: { title: { display: true, text: xCol, color: "#8890a4" } },
        y: { title: { display: true, text: yCol, color: "#8890a4" } },
      },
    }),
  });
}

function computeBins(values, binCount) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) return { labels: [String(min)], counts: [values.length] };
  const width = (max - min) / binCount;
  const counts = new Array(binCount).fill(0);
  values.forEach((v) => {
    let idx = Math.floor((v - min) / width);
    if (idx >= binCount) idx = binCount - 1;
    counts[idx]++;
  });
  const labels = counts.map((_, i) => (min + i * width).toFixed(1));
  return { labels, counts };
}

function buildHistogram(canvas, raw, col) {
  const values = raw.rows.map((r) => r[col]).filter((v) => v !== null && v !== undefined);
  const { labels, counts } = computeBins(values, Math.min(20, Math.max(5, Math.round(Math.sqrt(values.length)))));
  return new Chart(canvas, {
    type: "bar",
    data: { labels, datasets: [{ label: col, data: counts, backgroundColor: "#028090" }] },
    options: baseChartOptions({ plugins: { legend: { display: false } } }),
  });
}

function buildScoreChart(canvas, method, result) {
  const scoreKey = method === "knn" ? "knn_distance" : "anomaly_score";
  const rows = result.flagged.rows.slice();
  const labels = rows.map((r) => `id ${r._index}`);
  const values = rows.map((r) => r[scoreKey]);
  const threshold = result.model_settings ? result.model_settings.score_threshold : null;
  const datasets = [
    {
      type: "bar",
      label: method === "knn" ? "KNN distance" : "Anomaly score",
      data: values,
      backgroundColor: method === "knn" ? CHART_COLORS.knn : CHART_COLORS.isolation_forest,
    },
  ];
  if (threshold !== null) {
    datasets.push({
      type: "line",
      label: "Threshold",
      data: labels.map(() => threshold),
      borderColor: "#e8524d",
      borderDash: [6, 4],
      pointRadius: 0,
      borderWidth: 2,
    });
  }
  return new Chart(canvas, {
    type: "bar",
    data: { labels, datasets },
    options: baseChartOptions({ indexAxis: "y" }),
  });
}

function renderVisualizations(data) {
  if (!data.raw_numeric || data.raw_numeric.rows.length === 0) return "";
  const numCols = data.raw_numeric.columns;
  if (numCols.length === 0) return "";

  const xOptions = numCols.map((c, i) => `<option value="${c}" ${i === 0 ? "selected" : ""}>${c}</option>`).join("");
  const yOptions = numCols.map((c, i) => `<option value="${c}" ${i === 1 ? "selected" : (numCols.length === 1 ? "selected" : "")}>${c}</option>`).join("");
  const histOptions = numCols.map((c, i) => `<option value="${c}" ${i === 0 ? "selected" : ""}>${c}</option>`).join("");

  const scoreCharts = data.results
    ? Object.keys(data.results)
        .filter((name) => data.results[name].flagged.rows.length > 0)
        .map(
          (name) =>
            `<div class="chart-box"><h4>${name === "knn" ? "KNN distance" : "Isolation Forest anomaly score"} (flagged rows)</h4><canvas id="chart-score-${name}"></canvas></div>`
        )
        .join("")
    : "";

  const truncNote = data.raw_numeric_truncated
    ? `<p class="truncation-note">Showing the first ${data.raw_numeric.rows.length} rows in charts (file has more rows than the chart limit).</p>`
    : "";

  return `
    <div class="card">
      <h2>Visualizations</h2>
      ${truncNote}
      <div class="chart-controls">
        <label>X axis <select id="scatter-x">${xOptions}</select></label>
        <label>Y axis <select id="scatter-y">${yOptions}</select></label>
        <label>Histogram column <select id="hist-col">${histOptions}</select></label>
      </div>
      <div class="chart-grid">
        <div class="chart-box"><h4>Scatter - colored by which method flagged each row</h4><canvas id="chart-scatter"></canvas></div>
        <div class="chart-box"><h4>Distribution</h4><canvas id="chart-hist"></canvas></div>
        ${scoreCharts}
      </div>
    </div>`;
}

function wireVisualizations(data) {
  if (!data.raw_numeric || data.raw_numeric.rows.length === 0) return;
  const scatterX = document.getElementById("scatter-x");
  const scatterY = document.getElementById("scatter-y");
  const histCol = document.getElementById("hist-col");
  if (!scatterX) return;

  function redrawScatter() {
    const idx = activeCharts.findIndex((c) => c.canvas.id === "chart-scatter");
    if (idx !== -1) activeCharts.splice(idx, 1)[0].destroy();
    const chart = buildScatterChart(
      document.getElementById("chart-scatter"),
      data.raw_numeric,
      data.flagged_by || {},
      scatterX.value,
      scatterY.value
    );
    activeCharts.push(chart);
  }
  function redrawHist() {
    const idx = activeCharts.findIndex((c) => c.canvas.id === "chart-hist");
    if (idx !== -1) activeCharts.splice(idx, 1)[0].destroy();
    const chart = buildHistogram(document.getElementById("chart-hist"), data.raw_numeric, histCol.value);
    activeCharts.push(chart);
  }

  scatterX.addEventListener("change", redrawScatter);
  scatterY.addEventListener("change", redrawScatter);
  histCol.addEventListener("change", redrawHist);

  redrawScatter();
  redrawHist();

  if (data.results) {
    Object.entries(data.results).forEach(([name, result]) => {
      const canvas = document.getElementById(`chart-score-${name}`);
      if (canvas && result.flagged.rows.length > 0) {
        activeCharts.push(buildScoreChart(canvas, name, result));
      }
    });
  }
}

// ---------------------------------------------------------------------------
// Results rendering
// ---------------------------------------------------------------------------
function detectorLabel(name) {
  return name === "isolation_forest" ? "Isolation Forest" : "KNN";
}

function modelSettingsLine(settings) {
  if (!settings) return "";
  if (settings.method === "knn") {
    return `Model: KNN (k=${settings.k}), standardised features. Rows with a distance above ${settings.score_threshold.toFixed(4)} are flagged.`;
  }
  return `Model: IsolationForest with ${settings.n_estimators} trees. Rows scoring below ${settings.score_threshold.toFixed(4)} are flagged.`;
}

function renderDetector(name, result) {
  const parts = [`<h3>${detectorLabel(name)}</h3>`];
  if (result.model_settings) parts.push(`<div class="model-line">${modelSettingsLine(result.model_settings)}</div>`);
  if (result.dropped_columns.length) {
    parts.push(`<p class="note-line">Excluded column(s) with no numeric data at all: ${result.dropped_columns.join(", ")}</p>`);
  }
  parts.push(`<div class="stat-row"><span>Scored <b>${result.scored_rows}</b> of <b>${result.total_rows}</b> rows</span>`);
  if (result.imputed && result.imputed_row_count > 0) {
    const methodLabel = result.impute_method === "knn" ? "KNN imputation" : "the column median";
    parts.push(`<span>Filled missing values in <b>${result.imputed_row_count}</b> row(s) with ${methodLabel}</span>`);
  } else if (!result.imputed && result.skipped_rows > 0) {
    parts.push(`<span>Skipped <b>${result.skipped_rows}</b> row(s) with missing values</span>`);
  }
  parts.push(`<span>Flagged <b>${result.flagged_count}</b> outlier row(s)</span></div>`);
  parts.push(renderTableCard(null, result.flagged, { filename: `${name}_flagged.csv` }));
  return parts.join("\n");
}

function renderComparison(comparison) {
  const parts = [`<h2>Comparison - Isolation Forest vs KNN</h2>`];
  parts.push(
    `<div class="stat-tiles">` +
      `<div class="stat-tile"><span class="tile-value">${comparison.isolation_forest_count}</span><span class="tile-label">Isolation Forest flagged</span></div>` +
      `<div class="stat-tile"><span class="tile-value">${comparison.knn_count}</span><span class="tile-label">KNN flagged</span></div>` +
      `<div class="stat-tile"><span class="tile-value">${comparison.both_count}</span><span class="tile-label">Flagged by both</span></div>` +
      `<div class="stat-tile"><span class="tile-value">${comparison.union_count}</span><span class="tile-label">Distinct rows total</span></div>` +
      (comparison.agreement !== null
        ? `<div class="stat-tile"><span class="tile-value">${(comparison.agreement * 100).toFixed(0)}%</span><span class="tile-label">Agreement</span></div>`
        : "") +
      (comparison.rank_correlation !== null
        ? `<div class="stat-tile"><span class="tile-value">${comparison.rank_correlation.toFixed(3)}</span><span class="tile-label">Score rank correlation</span></div>`
        : "") +
      `</div>`
  );
  parts.push(`<p class="note-line">Rows flagged by both methods are the high-confidence outliers, shown first and highlighted.</p>`);
  parts.push(
    renderTableCard(null, comparison.consensus, {
      rowClass: (row) => (row.flagged_by === "both" ? "flagged-both" : ""),
      filename: "comparison.csv",
    })
  );
  return parts.join("\n");
}

function renderImputationComparison(imputationComparison) {
  const active = imputationComparison.active_method === "knn" ? "KNN" : "median";
  const other = imputationComparison.active_method === "knn" ? "median" : "KNN";
  const parts = [`<h2>Imputation Comparison - Median vs KNN</h2>`];
  parts.push(
    `<p class="note-line">Scoring used <b>${active}</b> imputation. For every originally-missing cell, here is what ${active} filled in versus what ${other} would have filled in instead.</p>`
  );
  parts.push(renderTableCard(null, imputationComparison.table, { showIndex: true, filename: "imputation_comparison.csv" }));
  return parts.join("\n");
}

function renderExportSection() {
  return `
    <div class="card" style="text-align: center; padding: 24px;">
      <h2>Export Cleaned Dataset</h2>
      <p class="note-line">Download your dataset with all missing values and explicit zeros resolved using your selected imputation method.</p>
      <button type="button" class="primary-btn" onclick="downloadCleanedCSV()" style="margin-top: 10px;">
        📥 Download Cleaned / Imputed CSV
      </button>
    </div>
  `;
}

function render(data) {
  Object.keys(tableState).forEach((k) => delete tableState[k]);
  destroyCharts();
  const parts = [];

  const missingTotal = data.columns_info.rows.reduce((sum, r) => sum + (r.missing || 0), 0);
  const numericCount = data.numeric_summary ? data.numeric_summary.rows.length : 0;

  parts.push(`<div class="card"><h2>Dataset Overview</h2>`);
  parts.push(
    `<div class="stat-tiles">` +
      `<div class="stat-tile"><span class="tile-value">${data.rows}</span><span class="tile-label">Rows</span></div>` +
      `<div class="stat-tile"><span class="tile-value">${data.columns}</span><span class="tile-label">Columns</span></div>` +
      `<div class="stat-tile"><span class="tile-value">${numericCount}</span><span class="tile-label">Numeric columns</span></div>` +
      `<div class="stat-tile"><span class="tile-value">${missingTotal}</span><span class="tile-label">Missing cells</span></div>` +
      `</div>`
  );
  parts.push(renderTableCard("Column dtypes &amp; missing values", data.columns_info, { filename: "columns_info.csv" }));
  parts.push(`</div>`);

  if (!data.has_numeric) {
    parts.push(`<div class="card"><p class="note-line">No numeric columns found - statistics and outlier detection were skipped.</p></div>`);
    resultsEl.innerHTML = parts.join("\n");
    resultsEl.classList.remove("hidden");
    drawAllTables();
    return;
  }

  parts.push(`<div class="card"><h2>Numeric Column Statistics</h2>`);
  parts.push(renderTableCard("Central tendency, spread &amp; kurtosis", data.numeric_summary, { filename: "numeric_summary.csv" }));
  parts.push(renderTableCard("Five-point summary", data.five_point_summary, { filename: "five_point_summary.csv" }));
  parts.push(`</div>`);

  parts.push(`<div class="card"><h2>Covariance Matrix</h2>`);
  parts.push(renderTableCard(null, data.covariance_matrix, { filename: "covariance_matrix.csv" }));
  parts.push(`</div>`);

  if (data.imputation_comparison) {
    parts.push(`<div class="card">${renderImputationComparison(data.imputation_comparison)}</div>`);
  }

  parts.push(renderVisualizations(data));

  parts.push(`<div class="card"><h2>Outlier Detection</h2>`);
  Object.entries(data.results).forEach(([name, result]) => {
    parts.push(renderDetector(name, result));
  });
  parts.push(`</div>`);

  if (data.comparison) {
    parts.push(`<div class="card">${renderComparison(data.comparison)}</div>`);
  }

  // Export card appended at bottom
  parts.push(renderExportSection());

  resultsEl.innerHTML = parts.join("\n");
  resultsEl.classList.remove("hidden");
  drawAllTables();
  wireVisualizations(data);
}

// ---------------------------------------------------------------------------
// Analyze trigger
// ---------------------------------------------------------------------------
function setLoading(isLoading) {
  analyzeBtn.disabled = isLoading;
  analyzeBtn.querySelector(".spinner").classList.toggle("hidden", !isLoading);
  analyzeBtn.querySelector(".btn-label").textContent = isLoading ? "Analyzing..." : "Analyze";
}

analyzeBtn.addEventListener("click", async () => {
  if (!currentFile) {
    showStatus("error", "Choose a CSV file first, or pick one of the samples.");
    return;
  }

  const form = new FormData();
  form.append("file", currentFile);
  form.append("method", methodSelect.value);
  form.append("contamination", document.getElementById("opt-contamination").value);
  form.append("k", document.getElementById("opt-k").value);
  form.append("impute", document.getElementById("opt-impute").checked ? "true" : "false");
  form.append("impute_method", imputeMethodSelect.value);
  form.append("impute_k", document.getElementById("opt-impute-k").value);

  setLoading(true);
  resultsEl.classList.add("hidden");
  showStatus("loading", "Analyzing...");

  try {
    const resp = await fetch("/api/analyze", { method: "POST", body: form });
    const data = await resp.json();
    if (!resp.ok) {
      showStatus("error", data.error || "Something went wrong.");
      return;
    }
    showStatus("", "");
    render(data);
  } catch (err) {
    showStatus("error", "Could not reach the server. Please try again.");
  } finally {
    setLoading(false);
  }
});