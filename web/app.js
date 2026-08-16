// app.js
//
// Starts Python inside the browser, hands it the same five files the
// desktop app uses, and draws whatever comes back. All of the thinking
// still happens in engine.py; this file only asks questions and paints
// the answers.

'use strict';

// the five modules that hold the maths, plus the bridge that wraps them
const PYTHON_MODULES = ['linalg', 'stats', 'models', 'dataset', 'engine'];

// matches the Okabe-Ito palette in graphview.py, so a model keeps the
// same colour on the website that it has in the desktop app
const CURVE_COLORS = [
  '#0072b2', // linear
  '#d55e00', // quadratic
  '#009e73', // cubic
  '#cc79a7', // exponential
  '#e69f00', // power
  '#56b4e9', // logarithmic
  '#000000'  // flatline
];

let bridge = null;       // the python module, once it is loaded
let samples = [];        // the built in datasets, read from python
let points = [];         // whatever is currently being fitted
let latest = null;       // the most recent analysis
let selectedName = null; // which model's card is open
let undoStack = [];
let view = { xMin: 0, xMax: 10, yMin: 0, yMax: 10 };


// ---------------------------------------------------------------
// small helpers
// ---------------------------------------------------------------

function byId(id) { return document.getElementById(id); }

function show(id, isVisible) { byId(id).hidden = !isVisible; }

function formatScore(value, decimals = 4) {
  if (value === null || value === undefined) return 'n/a';
  if (value !== 0 && Math.abs(value) < 0.001) return value.toExponential(2);
  return value.toFixed(decimals);
}

// 3 rather than 3.0000, but keep real decimals
function trimNumber(value) {
  if (value === null || value === undefined) return '';
  const rounded = Math.round(value * 10000) / 10000;
  return String(rounded);
}

function colorFor(result) {
  return CURVE_COLORS[result.colorIndex] || '#808080';
}

function resultNamed(name) {
  if (!latest) return null;
  return latest.results.find(r => r.name === name) || null;
}

function selectedResult() {
  return resultNamed(selectedName) || (latest && latest.results[0]) || null;
}

function reportFailure(error) {
  show('booting', false);
  show('failed', true);
  byId('failureText').textContent = String(error);
  console.error(error);
}


// ---------------------------------------------------------------
// starting python
// ---------------------------------------------------------------

async function fetchText(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`could not load ${path} (${response.status})`);
  }
  return response.text();
}

async function boot() {
  try {
    byId('bootStatus').textContent = 'Downloading Python…';
    const pyodide = await loadPyodide();

    byId('bootStatus').textContent = 'Loading VeriFit…';
    pyodide.FS.mkdir('/verifit');
    // the website reads the maths straight out of src/, so there is
    // only ever one copy of it and it cannot drift from the app
    for (const name of PYTHON_MODULES) {
      pyodide.FS.writeFile(`/verifit/${name}.py`,
                           await fetchText(`src/${name}.py`));
    }
    pyodide.FS.writeFile('/verifit/bridge.py',
                         await fetchText('web/bridge.py'));

    pyodide.runPython("import sys; sys.path.insert(0, '/verifit')");
    bridge = pyodide.runPython('import bridge; bridge');

    samples = JSON.parse(bridge.samples());
    buildSampleButtons();
    connectControls();

    // a shared link carries its own data; otherwise start with a sample
    if (!loadFromLink()) loadSample(0);

    show('booting', false);
    show('app', true);
    drawGraph();
  } catch (error) {
    reportFailure(error);
  }
}


// ---------------------------------------------------------------
// asking python for an answer
// ---------------------------------------------------------------

// every change to the data comes through here
function analyze(options = {}) {
  latest = JSON.parse(bridge.analyze(JSON.stringify(points)));
  if (!resultNamed(selectedName)) {
    selectedName = latest.results.length > 0 ? latest.results[0].name : null;
  }
  if (!options.keepTable) renderTable();
  renderFooter();
  renderVerdict();
  renderWarnings();
  renderRanking();
  renderUnavailable();
  drawGraph();
  renderTab();
}

function remember() {
  undoStack.push(JSON.parse(JSON.stringify(points)));
  if (undoStack.length > 60) undoStack.shift();
}

function undo() {
  if (undoStack.length === 0) return;
  points = undoStack.pop();
  analyze();
}


// ---------------------------------------------------------------
// samples and the top bar
// ---------------------------------------------------------------

function buildSampleButtons() {
  const holder = byId('sampleButtons');
  holder.innerHTML = '';
  samples.forEach((sample, index) => {
    const button = document.createElement('button');
    button.textContent = sample.label;
    button.title = sample.hint;
    button.addEventListener('click', () => loadSample(index));
    holder.appendChild(button);
  });
}

function markActiveSample(index) {
  document.querySelectorAll('#sampleButtons button').forEach((button, i) => {
    button.classList.toggle('active', i === index);
  });
}

function loadSample(index) {
  remember();
  // a fresh dataset forgets which curves were switched on, so the top
  // three show again, the same way the desktop app behaves
  bridge.reset();
  points = samples[index].points.map(p => ({ x: p.x, y: p.y, excluded: false }));
  selectedName = null;
  markActiveSample(index);
  analyze();
  reframe();
}

function connectControls() {
  byId('reframeButton').addEventListener('click', reframe);
  document.querySelectorAll('.rowButtons button').forEach(button => {
    button.addEventListener('click', () => {
      const action = button.dataset.action;
      if (action === 'undo') return undo();
      remember();
      if (action === 'clear') points = [];
      if (action === 'includeAll') points.forEach(p => { p.excluded = false; });
      markActiveSample(-1);
      analyze();
    });
  });
  connectGraph();
  connectTabs();
  connectDialogs();
}


// ---------------------------------------------------------------
// the data table
// ---------------------------------------------------------------

function renderTable() {
  const body = byId('dataBody');
  body.innerHTML = '';
  points.forEach((point, index) => {
    body.appendChild(buildRow(point, index));
  });
  body.appendChild(buildDraftRow());
}

function buildCell(point, index, key) {
  const cell = document.createElement('td');
  const input = document.createElement('input');
  input.type = 'text';
  input.inputMode = 'decimal';
  input.value = trimNumber(point[key]);
  input.addEventListener('input', () => {
    const parsed = parseNumber(input.value);
    input.classList.toggle('bad', parsed === null);
    if (parsed === null) return;
    points[index][key] = parsed;
    // the table is left alone so the cursor stays where it is
    analyze({ keepTable: true });
    markActiveSample(-1);
  });
  input.addEventListener('focus', () => remember());
  cell.appendChild(input);
  return cell;
}

function buildRow(point, index) {
  const row = document.createElement('tr');
  if (point.excluded) row.className = 'excluded';

  const markCell = document.createElement('td');
  markCell.className = 'markCol';
  const mark = document.createElement('button');
  mark.className = 'rowNumber';
  mark.textContent = String(index + 1);
  mark.title = point.excluded ? 'put this point back in the fit'
                              : 'leave this point out of the fit';
  mark.addEventListener('click', () => {
    remember();
    points[index].excluded = !points[index].excluded;
    analyze();
  });
  markCell.appendChild(mark);

  const deleteCell = document.createElement('td');
  const remove = document.createElement('button');
  remove.className = 'rowDelete';
  remove.textContent = '×';
  remove.title = 'delete this point';
  remove.addEventListener('click', () => {
    remember();
    points.splice(index, 1);
    analyze();
  });
  deleteCell.appendChild(remove);

  row.append(markCell, buildCell(point, index, 'x'),
             buildCell(point, index, 'y'), deleteCell);
  return row;
}

// the blank row at the bottom becomes a real point once both cells hold
// a number, which is how you add data by typing
function buildDraftRow() {
  const row = document.createElement('tr');
  row.className = 'draft';

  const markCell = document.createElement('td');
  markCell.className = 'markCol';
  const plus = document.createElement('span');
  plus.className = 'rowNumber';
  plus.textContent = '+';
  markCell.appendChild(plus);

  const draft = { x: '', y: '' };
  const cells = {};
  for (const key of ['x', 'y']) {
    const cell = document.createElement('td');
    const input = document.createElement('input');
    input.type = 'text';
    input.inputMode = 'decimal';
    input.placeholder = key;
    input.addEventListener('input', () => {
      draft[key] = input.value;
      const x = parseNumber(draft.x);
      const y = parseNumber(draft.y);
      if (x === null || y === null) return;
      remember();
      points.push({ x, y, excluded: false });
      markActiveSample(-1);
      analyze();
      // carry on typing in the new blank row
      const inputs = byId('dataBody').querySelectorAll('tr.draft input');
      if (inputs.length > 0) inputs[0].focus();
    });
    cells[key] = input;
    cell.appendChild(input);
    row.appendChild(key === 'x' ? cell : cell);
  }
  row.insertBefore(markCell, row.firstChild);
  row.appendChild(document.createElement('td'));
  return row;
}

function parseNumber(text) {
  if (typeof text !== 'string') return null;
  const trimmed = text.trim();
  if (trimmed === '') return null;
  const value = Number(trimmed);
  if (!Number.isFinite(value)) return null;
  return value;
}

function renderFooter() {
  const active = points.filter(p => !p.excluded).length;
  let text = `${points.length} rows, ${active} active`;
  if (latest && latest.usesOffset) {
    text += ` · x shifted by ${trimNumber(latest.xOffset)} for fitting`;
  }
  byId('tableFooter').textContent = text;
}


// ---------------------------------------------------------------
// the models panel
// ---------------------------------------------------------------

function renderVerdict() {
  const box = byId('verdict');
  box.textContent = latest.verdict;
  box.hidden = latest.verdict === '';
}

function renderWarnings() {
  const holder = byId('warnings');
  holder.innerHTML = '';
  for (const warning of latest.warnings) {
    const line = document.createElement('div');
    line.className = 'warning';
    line.textContent = warning;
    holder.appendChild(line);
  }
}

function renderRanking() {
  const list = byId('ranking');
  list.innerHTML = '';
  if (latest.results.length === 0) {
    list.innerHTML = '<li class="muted small" style="padding:6px 0">' +
                     'No model fitted yet. Add points, or try a sample.</li>';
    return;
  }
  latest.results.forEach((result, index) => {
    const item = document.createElement('li');
    if (result.name === selectedName) item.classList.add('selected');

    const row = document.createElement('div');
    row.className = 'rankRow';

    const swatch = document.createElement('span');
    swatch.className = 'swatch';
    swatch.style.background = result.isVisible ? colorFor(result) : 'transparent';
    swatch.style.border = `1px solid ${colorFor(result)}`;
    swatch.title = result.isVisible ? 'hide this curve' : 'show this curve';
    swatch.addEventListener('click', event => {
      event.stopPropagation();
      bridge.setVisible(result.name, !result.isVisible);
      analyze({ keepTable: true });
    });

    const rank = document.createElement('span');
    rank.className = 'rank';
    rank.textContent = `${index + 1}.`;

    const name = document.createElement('span');
    name.className = 'modelName';
    name.textContent = result.name;

    const score = document.createElement('span');
    score.className = 'score';
    score.textContent = formatScore(result.cvRmse);
    score.title = 'cross-validated error, smaller is better';

    row.append(swatch, rank, name, score);
    row.addEventListener('click', () => {
      selectedName = (selectedName === result.name) ? null : result.name;
      renderRanking();
      drawGraph();
      renderTab();
    });

    item.appendChild(row);
    if (result.name === selectedName) item.appendChild(buildDetail(result));
    list.appendChild(item);
  });
}

function buildDetail(result) {
  const detail = document.createElement('div');
  detail.className = 'detail';

  const equation = document.createElement('div');
  equation.className = 'equation';
  equation.textContent = result.equation;
  detail.appendChild(equation);

  const scores = document.createElement('div');
  scores.className = 'muted';
  scores.textContent = `training RMSE ${formatScore(result.trainRmse)}` +
                       `   R² ${formatScore(result.r2)}`;
  detail.appendChild(scores);

  if (result.weight === null) {
    const note = document.createElement('div');
    note.className = 'muted';
    note.textContent = 'AICc n/a: too few points for this many parameters';
    detail.appendChild(note);
  } else {
    const bar = document.createElement('div');
    bar.className = 'weightBar';
    const fill = document.createElement('span');
    fill.style.width = `${Math.max(1, result.weight * 100)}%`;
    bar.appendChild(fill);
    detail.appendChild(bar);
    const label = document.createElement('div');
    label.className = 'muted';
    label.textContent = `${Math.round(result.weight * 100)}% of AICc support`;
    detail.appendChild(label);
  }

  if (result.isAdjusted) {
    const note = document.createElement('div');
    note.className = 'modelWarning';
    note.textContent = 'adjusted by hand: CV and AICc no longer apply';
    detail.appendChild(note);
  }

  for (const warning of result.warnings) {
    const line = document.createElement('div');
    line.className = 'modelWarning';
    line.textContent = warning;
    detail.appendChild(line);
  }
  return detail;
}

function renderUnavailable() {
  const holder = byId('unavailable');
  if (latest.unavailable.length === 0) {
    holder.textContent = '';
    return;
  }
  holder.textContent = 'not fitted — ' + latest.unavailable
    .map(item => `${item.name}: ${item.reason}`).join(' · ');
}


// ---------------------------------------------------------------
// the graph
// ---------------------------------------------------------------

// the same padding rule as padRange in graphview.py
function padRange(low, high) {
  if (low === high) {
    const size = low !== 0 ? Math.abs(low) * 0.1 : 1;
    return [low - size, high + size];
  }
  const margin = (high - low) * 0.08;
  return [low - margin, high + margin];
}

function reframe() {
  if (points.length === 0) {
    view = { xMin: 0, xMax: 10, yMin: 0, yMax: 10 };
  } else {
    const xs = points.map(p => p.x);
    const ys = points.map(p => p.y);
    const [xMin, xMax] = padRange(Math.min(...xs), Math.max(...xs));
    const [yMin, yMax] = padRange(Math.min(...ys), Math.max(...ys));
    view = { xMin, xMax, yMin, yMax };
  }
  drawGraph();
}

const PAD = { left: 48, right: 16, top: 14, bottom: 32 };

function graphMetrics() {
  const canvas = byId('graph');
  const width = canvas.clientWidth;
  const height = Math.max(280, Math.round(width * 0.6));
  return { canvas, width, height };
}

function toScreenX(x, m) {
  return PAD.left + (x - view.xMin) / (view.xMax - view.xMin)
         * (m.width - PAD.left - PAD.right);
}

function toScreenY(y, m) {
  return m.height - PAD.bottom - (y - view.yMin) / (view.yMax - view.yMin)
         * (m.height - PAD.top - PAD.bottom);
}

function toDataX(px, m) {
  return view.xMin + (px - PAD.left) / (m.width - PAD.left - PAD.right)
         * (view.xMax - view.xMin);
}

function toDataY(py, m) {
  return view.yMin + (m.height - PAD.bottom - py)
         / (m.height - PAD.top - PAD.bottom) * (view.yMax - view.yMin);
}

// round tick positions, the same 1 / 2 / 5 rule graphview.py uses
function niceStep(rough) {
  if (rough <= 0) return 1;
  const power = Math.floor(Math.log10(rough));
  const base = Math.pow(10, power);
  for (const multiple of [1, 2, 5]) {
    if (rough <= multiple * base) return multiple * base;
  }
  return 10 * base;
}

function ticksBetween(low, high, step) {
  const values = [];
  if (step <= 0 || high <= low) return values;
  for (let i = Math.ceil(low / step); i <= Math.floor(high / step); i++) {
    values.push(i * step);
  }
  return values;
}

function drawGraph() {
  const m = graphMetrics();
  const ratio = window.devicePixelRatio || 1;
  m.canvas.width = m.width * ratio;
  m.canvas.height = m.height * ratio;
  m.canvas.style.height = `${m.height}px`;
  const ctx = m.canvas.getContext('2d');
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.clearRect(0, 0, m.width, m.height);

  const xStep = niceStep((view.xMax - view.xMin) / 9);
  const yStep = niceStep((view.yMax - view.yMin) / 7);

  // the faint in-between lines first, then the main grid over them,
  // the way desmos layers its paper
  drawGridLines(ctx, m, xStep / 5, yStep / 5, '#f2f2f4');
  drawGridLines(ctx, m, xStep, yStep, '#e2e4e8');

  // the axes themselves, when they are in view
  ctx.strokeStyle = '#8b9099';
  ctx.lineWidth = 1;
  if (view.xMin <= 0 && 0 <= view.xMax) {
    const px = Math.round(toScreenX(0, m)) + 0.5;
    line(ctx, px, PAD.top, px, m.height - PAD.bottom);
  }
  if (view.yMin <= 0 && 0 <= view.yMax) {
    const py = Math.round(toScreenY(0, m)) + 0.5;
    line(ctx, PAD.left, py, m.width - PAD.right, py);
  }

  if (latest) {
    drawBand(ctx, m);
    drawCurves(ctx, m);
  }
  drawPoints(ctx, m);
  drawTickLabels(ctx, m, xStep, yStep);

  ctx.strokeStyle = '#cdd1d6';
  ctx.strokeRect(PAD.left + 0.5, PAD.top + 0.5,
                 m.width - PAD.left - PAD.right - 1,
                 m.height - PAD.top - PAD.bottom - 1);

  if (points.filter(p => !p.excluded).length < 2) {
    ctx.fillStyle = '#9aa1aa';
    ctx.font = '14px Ubuntu, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Click anywhere to add points, or pick a sample above.',
                 m.width / 2, m.height / 2);
  }
}

function line(ctx, x1, y1, x2, y2) {
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();
}

function drawGridLines(ctx, m, xStep, yStep, color) {
  ctx.strokeStyle = color;
  ctx.lineWidth = 1;
  for (const x of ticksBetween(view.xMin, view.xMax, xStep)) {
    const px = Math.round(toScreenX(x, m)) + 0.5;
    line(ctx, px, PAD.top, px, m.height - PAD.bottom);
  }
  for (const y of ticksBetween(view.yMin, view.yMax, yStep)) {
    const py = Math.round(toScreenY(y, m)) + 0.5;
    line(ctx, PAD.left, py, m.width - PAD.right, py);
  }
}

function drawTickLabels(ctx, m, xStep, yStep) {
  ctx.font = '11px Ubuntu, sans-serif';
  ctx.fillStyle = '#5f646b';
  ctx.textAlign = 'center';
  for (const x of ticksBetween(view.xMin, view.xMax, xStep)) {
    ctx.fillText(trimNumber(x), toScreenX(x, m), m.height - PAD.bottom + 15);
  }
  ctx.textAlign = 'right';
  for (const y of ticksBetween(view.yMin, view.yMax, yStep)) {
    ctx.fillText(trimNumber(y), PAD.left - 7, toScreenY(y, m) + 4);
  }
}

// the curves are asked for one at a time so that python keeps ownership
// of where each model can and cannot be drawn
function drawCurves(ctx, m) {
  for (const result of latest.results) {
    if (!result.isVisible) continue;
    const pieces = JSON.parse(
      bridge.curve(result.name, view.xMin, view.xMax, 240));
    ctx.strokeStyle = colorFor(result);
    ctx.lineWidth = result.name === selectedName ? 2.5 : 1.8;
    for (const piece of pieces) {
      ctx.beginPath();
      piece.forEach(([x, y], i) => {
        const px = toScreenX(x, m);
        const py = toScreenY(y, m);
        if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
      });
      ctx.stroke();
    }
  }
}

// the range a new observation would probably land in, for the open
// model only. It flares away from the data, which is the extrapolation
// warning drawn as a picture.
function drawBand(ctx, m) {
  const result = selectedResult();
  if (!result || !result.isVisible) return;
  const pieces = JSON.parse(
    bridge.band(result.name, view.xMin, view.xMax, 90));
  ctx.fillStyle = colorFor(result);
  ctx.globalAlpha = 0.12;
  for (const piece of pieces) {
    if (piece.length < 2) continue;
    ctx.beginPath();
    piece.forEach(([x, low, high], i) => {
      const px = toScreenX(x, m);
      const py = toScreenY(high, m);
      if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    });
    for (let i = piece.length - 1; i >= 0; i--) {
      const [x, low] = piece[i];
      ctx.lineTo(toScreenX(x, m), toScreenY(low, m));
    }
    ctx.closePath();
    ctx.fill();
  }
  ctx.globalAlpha = 1;
}

function drawPoints(ctx, m) {
  points.forEach((point, index) => {
    const px = toScreenX(point.x, m);
    const py = toScreenY(point.y, m);
    if (px < PAD.left || px > m.width - PAD.right) return;
    if (py < PAD.top || py > m.height - PAD.bottom) return;
    const result = selectedResult();
    const isOutlier = result && result.outlierIndex !== null &&
                      activeIndexOf(index) === result.outlierIndex;
    ctx.beginPath();
    ctx.arc(px, py, 4, 0, Math.PI * 2);
    if (point.excluded) {
      ctx.strokeStyle = '#9aa1aa';
      ctx.lineWidth = 2;
      ctx.stroke();
    } else {
      ctx.fillStyle = isOutlier ? '#c82828' : '#000';
      ctx.fill();
    }
  });
}

// residuals only cover the points being fitted, so a table row has to be
// translated into its place among the active points
function activeIndexOf(row) {
  let seen = 0;
  for (let i = 0; i < points.length; i++) {
    if (points[i].excluded) continue;
    if (i === row) return seen;
    seen++;
  }
  return null;
}


// ---------------------------------------------------------------
// clicking, dragging and zooming the graph
// ---------------------------------------------------------------

function connectGraph() {
  const canvas = byId('graph');
  let dragging = false;
  let moved = 0;
  let last = null;

  canvas.addEventListener('pointerdown', event => {
    dragging = true;
    moved = 0;
    last = { x: event.offsetX, y: event.offsetY };
    canvas.setPointerCapture(event.pointerId);
  });

  canvas.addEventListener('pointermove', event => {
    if (!dragging) return;
    const m = graphMetrics();
    const dx = event.offsetX - last.x;
    const dy = event.offsetY - last.y;
    moved += Math.abs(dx) + Math.abs(dy);
    const spanX = (view.xMax - view.xMin) / (m.width - PAD.left - PAD.right);
    const spanY = (view.yMax - view.yMin) / (m.height - PAD.top - PAD.bottom);
    view.xMin -= dx * spanX; view.xMax -= dx * spanX;
    view.yMin += dy * spanY; view.yMax += dy * spanY;
    last = { x: event.offsetX, y: event.offsetY };
    drawGraph();
  });

  canvas.addEventListener('pointerup', event => {
    dragging = false;
    // a press that did not really move is a click, and a click adds a
    // point where it landed
    if (moved > 5) return;
    const m = graphMetrics();
    if (event.offsetX < PAD.left || event.offsetX > m.width - PAD.right) return;
    if (event.offsetY < PAD.top || event.offsetY > m.height - PAD.bottom) return;
    remember();
    points.push({
      x: Math.round(toDataX(event.offsetX, m) * 10000) / 10000,
      y: Math.round(toDataY(event.offsetY, m) * 10000) / 10000,
      excluded: false
    });
    markActiveSample(-1);
    analyze();
  });

  canvas.addEventListener('wheel', event => {
    event.preventDefault();
    const factor = event.deltaY > 0 ? 1.12 : 0.89;
    const m = graphMetrics();
    // zoom toward the cursor, so the point under it stays put
    const cx = toDataX(event.offsetX, m);
    const cy = toDataY(event.offsetY, m);
    view.xMin = cx + (view.xMin - cx) * factor;
    view.xMax = cx + (view.xMax - cx) * factor;
    view.yMin = cy + (view.yMin - cy) * factor;
    view.yMax = cy + (view.yMax - cy) * factor;
    drawGraph();
  }, { passive: false });

  window.addEventListener('resize', () => drawGraph());
}


// the tabs under the graph and the dialogs are set up further down
function connectTabs() {}
function renderTab() {}
function connectDialogs() {}
function loadFromLink() { return false; }


boot();
