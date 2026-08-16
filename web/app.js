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

// How the graph window answers the mouse. Panning at 1 would pin the
// point under the cursor to it, which is standard but quick on a
// trackpad, so it is deliberately gentler. Zoom is worked out from how
// far the wheel really turned, so the many tiny scroll events a
// trackpad sends do not race away.
const PAN_SPEED = 0.55;
const ZOOM_SPEED = 0.0020;

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

    // a shared link carries its own data; otherwise the graph starts
    // empty, so the first thing on it is the visitor's own numbers
    if (!loadFromLink()) {
      points = [];
      markActiveSample(-1);
      analyze();
      reframe();
    }

    show('booting', false);
    show('app', true);
    // now that the panels have a real width, draw them for real
    drawGraph();
    renderTab();
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
  // the leave-one-out sweep describes the old data, so it is thrown away
  influenceReport = null;
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

// While a cell is being typed into, the state before the first keystroke
// is held here and only filed away once something really changes. Simply
// clicking through cells therefore does not fill the undo stack with
// copies of the same data.
let pendingUndo = null;

function rememberOnce() {
  if (pendingUndo === null) return;
  undoStack.push(pendingUndo);
  if (undoStack.length > 60) undoStack.shift();
  pendingUndo = null;
}

function undo() {
  if (undoStack.length === 0) return;
  points = undoStack.pop();
  analyze();
}


// ---------------------------------------------------------------
// samples and the top bar
// ---------------------------------------------------------------

// the Sample button opens a list of the built in datasets, and the one
// currently loaded stays marked, so you can see where you are
function buildSampleButtons() {
  const menu = byId('sampleMenu');
  menu.innerHTML = '';
  samples.forEach((sample, index) => {
    const button = document.createElement('button');
    button.innerHTML = `${sample.label}<span class="hint">${sample.hint}</span>`;
    button.addEventListener('click', () => {
      menu.hidden = true;
      loadSample(index);
    });
    menu.appendChild(button);
  });

  byId('sampleButton').addEventListener('click', event => {
    event.stopPropagation();
    menu.hidden = !menu.hidden;
  });
  // a click anywhere else puts the menu away
  document.addEventListener('click', event => {
    if (!menu.hidden && !menu.contains(event.target)) menu.hidden = true;
  });
}

function markActiveSample(index) {
  document.querySelectorAll('#sampleMenu button').forEach((button, i) => {
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
    rememberOnce();
    points[index][key] = parsed;
    // the table is left alone so the cursor stays where it is
    analyze({ keepTable: true });
    markActiveSample(-1);
  });
  input.addEventListener('focus', () => {
    pendingUndo = JSON.parse(JSON.stringify(points));
  });
  input.addEventListener('blur', () => { pendingUndo = null; });
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
  // an empty graph is a starting point, not a problem worth warning about
  if (points.length === 0) return;
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
                     'Nothing fitted yet. Click the graph to add points, ' +
                     'paste your own under Data, or open Sample.</li>';
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
  // with nothing entered every model is unavailable, and listing all
  // seven reasons says nothing useful
  if (latest.unavailable.length === 0 || points.length === 0) {
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

  // everything that follows the data is held inside the plot area, so a
  // steep curve or a wide band cannot spill over the axis labels
  ctx.save();
  ctx.beginPath();
  ctx.rect(PAD.left, PAD.top,
           m.width - PAD.left - PAD.right,
           m.height - PAD.top - PAD.bottom);
  ctx.clip();
  if (latest) {
    drawBand(ctx, m);
    drawCurves(ctx, m);
  }
  drawPoints(ctx, m);
  if (mode === 'predict' && predictX !== null) drawPredictMarker(ctx, m);
  ctx.restore();

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
    // the clip region trims anything hanging over the edge, so a point
    // half out of view still shows the half that is inside
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

// where the Predict tab is asking about, and what each visible model
// expects there
function drawPredictMarker(ctx, m) {
  const px = toScreenX(predictX, m);
  if (px < PAD.left || px > m.width - PAD.right) return;
  ctx.strokeStyle = '#7878c8';
  ctx.lineWidth = 1;
  line(ctx, px, PAD.top, px, m.height - PAD.bottom);
  for (const result of latest.results) {
    if (!result.isVisible) continue;
    const answer = JSON.parse(bridge.predict(result.name, predictX));
    if (answer.y === null) continue;
    const py = toScreenY(answer.y, m);
    if (py < PAD.top || py > m.height - PAD.bottom) continue;
    ctx.strokeStyle = colorFor(result);
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(px, py, 5, 0, Math.PI * 2);
    ctx.stroke();
  }
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
    const spanX = (view.xMax - view.xMin) / (m.width - PAD.left - PAD.right)
                  * PAN_SPEED;
    const spanY = (view.yMax - view.yMin) / (m.height - PAD.top - PAD.bottom)
                  * PAN_SPEED;
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
    // a mouse wheel notch sends a big deltaY and a trackpad sends a
    // stream of small ones, so the step follows the number rather than
    // its sign. The clamp stops a flick from jumping several times over.
    const factor = Math.min(2, Math.max(0.5,
                            Math.exp(event.deltaY * ZOOM_SPEED)));
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

  // the strip under the graph is a canvas too, so it has to be redrawn
  // at the new width rather than stretched
  window.addEventListener('resize', () => { drawGraph(); renderTab(); });
}


// ---------------------------------------------------------------
// the tabs under the graph
//
// Each one exists to help you doubt the winner rather than admire it.
// ---------------------------------------------------------------

const TABS = [
  ['Residuals', 'residuals'],
  ['Predict', 'predict'],
  ['Sensitivity', 'sensitivity'],
  ['Influence', 'influence'],
  ['R² vs CV', 'rsquared']
];

let mode = 'residuals';
let predictX = null;
let influenceReport = null;

function connectTabs() {
  const holder = byId('tabs');
  holder.innerHTML = '';
  for (const [label, key] of TABS) {
    const button = document.createElement('button');
    button.textContent = label;
    button.dataset.key = key;
    button.addEventListener('click', () => {
      mode = key;
      // the sweep refits everything once per point, so it is only run
      // when somebody actually opens the tab
      if (key === 'influence' && influenceReport === null) {
        influenceReport = JSON.parse(bridge.influence());
      }
      renderTab();
    });
    holder.appendChild(button);
  }
}

function renderTab() {
  document.querySelectorAll('#tabs button').forEach(button => {
    button.classList.toggle('active', button.dataset.key === mode);
  });
  const panel = byId('tabPanel');
  panel.innerHTML = '';
  if (!latest || latest.results.length === 0) {
    panel.innerHTML = '<p class="muted">Nothing fitted yet.</p>';
    return;
  }
  if (mode === 'residuals') renderResiduals(panel);
  else if (mode === 'predict') renderPredict(panel);
  else if (mode === 'sensitivity') renderSensitivity(panel);
  else if (mode === 'influence') renderInfluence(panel);
  else renderRSquared(panel);
}

// a small canvas that lines up with the graph above it
function stripCanvas(panel, height = 104) {
  const canvas = document.createElement('canvas');
  // a hidden panel measures zero, which would make an invisible canvas,
  // so fall back to a sensible width until the layout is real
  const width = Math.max(240, panel.clientWidth - 28);
  const ratio = window.devicePixelRatio || 1;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  panel.appendChild(canvas);
  const ctx = canvas.getContext('2d');
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  return { ctx, width, height };
}

function caption(panel, text, className = 'muted small') {
  const line = document.createElement('p');
  line.className = className;
  line.style.margin = '6px 0 0';
  line.textContent = text;
  panel.appendChild(line);
}

// ---------- residuals ----------

function renderResiduals(panel) {
  const result = selectedResult();
  if (!result || result.residuals.length === 0) {
    panel.innerHTML = '<p class="muted">Select a model to see its misses.</p>';
    return;
  }
  const { ctx, width, height } = stripCanvas(panel);
  const middle = height / 2;
  const activeXs = points.filter(p => !p.excluded).map(p => p.x);

  let biggest = 0;
  for (const value of result.residuals) {
    if (value !== null && Math.abs(value) > biggest) biggest = Math.abs(value);
  }
  if (biggest <= 0) biggest = 1;
  const reach = biggest * 1.25;

  ctx.strokeStyle = '#c9ced4';
  line(ctx, 0, middle, width, middle);

  result.residuals.forEach((value, i) => {
    if (value === null || i >= activeXs.length) return;
    const px = (activeXs[i] - view.xMin) / (view.xMax - view.xMin) * width;
    if (px < 0 || px > width) return;
    const py = middle - (value / reach) * (height / 2 - 6);
    ctx.strokeStyle = '#d8dce1';
    line(ctx, px, middle, px, py);
    ctx.fillStyle = (i === result.outlierIndex) ? '#c82828' : '#3c4148';
    ctx.beginPath();
    ctx.arc(px, py, 3, 0, Math.PI * 2);
    ctx.fill();
  });

  ctx.fillStyle = '#8b9099';
  ctx.font = '10px Ubuntu, sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText(`residuals: ${result.name}   ±${trimNumber(reach)}`, 2, 11);

  caption(panel, 'A model that fits well scatters its misses either side ' +
                 'of the line. A run of misses on one side means the data ' +
                 'bends in a way this model cannot follow.');
}

// ---------- predict ----------

function renderPredict(panel) {
  const controls = document.createElement('div');
  controls.className = 'predictControls';
  controls.innerHTML = '<span>Predict at x =</span>';

  const input = document.createElement('input');
  input.type = 'number';
  input.step = 'any';
  if (predictX !== null) input.value = predictX;
  input.addEventListener('input', () => {
    predictX = parseNumber(input.value);
    renderPredictRows(panel);
    drawGraph();
  });
  controls.appendChild(input);
  panel.appendChild(controls);

  const rows = document.createElement('div');
  rows.id = 'predictRows';
  panel.appendChild(rows);
  renderPredictRows(panel);
}

function renderPredictRows(panel) {
  const rows = panel.querySelector('#predictRows');
  if (!rows) return;
  rows.innerHTML = '';
  if (predictX === null) {
    rows.innerHTML = '<p class="muted small">Type an x value to see what ' +
                     'each model expects there, and how sure it is.</p>';
    return;
  }
  let shown = 0;
  for (const result of latest.results) {
    if (!result.isVisible) continue;
    const answer = JSON.parse(bridge.predict(result.name, predictX));
    const row = document.createElement('div');
    row.className = 'predictRow';

    const name = document.createElement('span');
    name.className = 'name';
    name.style.color = colorFor(result);
    name.textContent = result.name;

    const value = document.createElement('span');
    value.className = 'value';
    value.textContent = answer.y === null ? 'cannot predict here'
                                          : `y = ${formatScore(answer.y, 3)}`;

    const range = document.createElement('span');
    range.className = 'range';
    if (answer.low !== null && answer.high !== null) {
      range.textContent = `likely ${formatScore(answer.low, 3)} ` +
                          `to ${formatScore(answer.high, 3)}`;
    }

    row.append(name, value, range);
    rows.appendChild(row);
    shown++;
  }
  if (shown === 0) {
    rows.innerHTML = '<p class="muted small">No curve is switched on.</p>';
    return;
  }
  const answer = JSON.parse(bridge.predict(latest.results[0].name, predictX));
  if (answer.isExtrapolation) {
    const badge = document.createElement('p');
    badge.innerHTML = '<span class="badge">outside the data range</span> ' +
      '<span class="muted small">the models disagree most here, and the ' +
      'likely ranges widen to say so</span>';
    badge.style.margin = '8px 0 0';
    rows.appendChild(badge);
  }
}

// ---------- sensitivity ----------

function renderSensitivity(panel) {
  const result = selectedResult();
  if (!result) {
    panel.innerHTML = '<p class="muted">Select a model first.</p>';
    return;
  }
  const info = JSON.parse(bridge.parameters(result.name));
  if (info === null) {
    panel.innerHTML = '<p class="muted">No standard errors for this model. ' +
                      'It needs more points than it has parameters.</p>';
    return;
  }

  const heading = document.createElement('p');
  heading.className = 'muted small';
  heading.style.margin = '0 0 4px';
  heading.textContent = `${result.name}: drag a parameter within plus or ` +
                        'minus two standard errors and watch the curve move.';
  panel.appendChild(heading);

  const values = info.values.slice();
  info.names.forEach((name, index) => {
    const [low, high] = info.bounds[index];
    if (low === null || high === null) return;
    const row = document.createElement('div');
    row.className = 'sliderRow';

    const label = document.createElement('span');
    label.textContent = name;

    const slider = document.createElement('input');
    slider.type = 'range';
    slider.min = low;
    slider.max = high;
    slider.step = (high - low) / 200 || 0.0001;
    slider.value = values[index];

    const readout = document.createElement('span');
    readout.className = 'value';
    readout.textContent = formatScore(values[index], 4);

    slider.addEventListener('input', () => {
      values[index] = Number(slider.value);
      readout.textContent = formatScore(values[index], 4);
      latest = JSON.parse(bridge.setParams(result.name, JSON.stringify(values)));
      renderRanking();
      drawGraph();
    });

    row.append(label, slider, readout);
    panel.appendChild(row);
  });

  const reset = document.createElement('button');
  reset.textContent = 'Reset to the fitted values';
  reset.style.marginTop = '6px';
  reset.addEventListener('click', () => {
    latest = JSON.parse(bridge.refit());
    renderRanking();
    drawGraph();
    renderTab();
  });
  panel.appendChild(reset);

  if (result.isAdjusted) {
    caption(panel, 'This curve was moved by hand, so its cross-validation ' +
                   'and AICc scores no longer mean anything. Reset to get ' +
                   'them back.', 'alert small');
  }
}

// ---------- influence ----------

function renderInfluence(panel) {
  if (influenceReport === null) {
    influenceReport = JSON.parse(bridge.influence());
  }
  const report = influenceReport;
  if (report.winner === null || report.entries.length === 0) {
    panel.innerHTML = '<p class="muted">Not enough points yet — leaving one ' +
                      'out needs at least four.</p>';
    return;
  }

  const changers = report.entries.filter(entry => entry.changesWinner);
  const verdict = document.createElement('p');
  verdict.style.margin = '0 0 4px';
  if (changers.length === 0) {
    verdict.innerHTML = `<strong>${report.winner}</strong> stays the best ` +
      'model no matter which single point is removed. The ranking does not ' +
      'depend on any one point.';
  } else {
    const rows = changers.map(entry => entry.row + 1).join(', ');
    verdict.className = 'alert';
    verdict.innerHTML = `Removing row ${changers[0].row + 1} changes the ` +
      `best model from <strong>${report.winner}</strong> to ` +
      `<strong>${changers[0].winner}</strong>. ` +
      (changers.length === 1
        ? 'The conclusion rests on that one point. Try excluding it.'
        : `${changers.length} points change the answer on their own: rows ${rows}.`);
  }
  panel.appendChild(verdict);

  const { ctx, width, height } = stripCanvas(panel, 92);
  let biggest = 0;
  for (const entry of report.entries) {
    if (entry.cvShift !== null) biggest = Math.max(biggest, Math.abs(entry.cvShift));
  }
  const base = height - 20;
  ctx.strokeStyle = '#d6dae0';
  line(ctx, 0, base, width, base);
  if (biggest > 0) {
    for (const entry of report.entries) {
      const point = points[entry.row];
      if (!point || entry.cvShift === null) continue;
      const px = (point.x - view.xMin) / (view.xMax - view.xMin) * width;
      if (px < 0 || px > width) continue;
      const barHeight = Math.max(1, Math.abs(entry.cvShift) / biggest * (base - 6));
      ctx.fillStyle = entry.changesWinner ? '#c82828' : '#9aa1aa';
      ctx.fillRect(px - 3, base - barHeight, 6, barHeight);
      if (entry.changesWinner) {
        ctx.fillStyle = '#c82828';
        ctx.font = '9px Ubuntu, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(String(entry.row + 1), px, base - barHeight - 3);
      }
    }
  }
  ctx.fillStyle = '#8b9099';
  ctx.font = '10px Ubuntu, sans-serif';
  ctx.textAlign = 'left';
  ctx.fillText("how much the winner's error moves when each point is dropped",
               2, height - 2);
}

// ---------- R squared against cross-validation ----------

function renderRSquared(panel) {
  const byR2 = latest.results.filter(r => r.r2 !== null)
    .slice().sort((a, b) => b.r2 - a.r2);
  const byCv = latest.results.filter(r => r.cvRmse !== null)
    .slice().sort((a, b) => a.cvRmse - b.cvRmse);
  if (byR2.length === 0 || byCv.length === 0) {
    panel.innerHTML = '<p class="muted">No scores to compare yet.</p>';
    return;
  }

  const { ctx, width, height } = stripCanvas(panel, 34 + byR2.length * 15);
  const leftX = 128;
  const rightX = width - 128;
  const top = 30;
  const rowY = (index, total) =>
    top + index * ((height - top - 6) / Math.max(1, total - 1));

  ctx.font = '10px Ubuntu, sans-serif';
  ctx.fillStyle = '#8b9099';
  ctx.textAlign = 'right';
  ctx.fillText('ranked by R²', leftX, 12);
  ctx.textAlign = 'left';
  ctx.fillText('ranked by cross-validation', rightX + 6, 12);

  byR2.forEach((result, leftIndex) => {
    const rightIndex = byCv.indexOf(result);
    if (rightIndex < 0) return;
    const y1 = rowY(leftIndex, byR2.length);
    const y2 = rowY(rightIndex, byCv.length);
    const crossed = leftIndex !== rightIndex;
    ctx.strokeStyle = crossed ? colorFor(result) : '#dcdfe4';
    ctx.lineWidth = crossed ? 2 : 1;
    line(ctx, leftX + 4, y1, rightX - 4, y2);
  });

  ctx.font = '11px Ubuntu, sans-serif';
  byR2.forEach((result, index) => {
    ctx.fillStyle = colorFor(result);
    ctx.textAlign = 'right';
    ctx.fillText(`${result.name} ${formatScore(result.r2, 3)}`,
                 leftX, rowY(index, byR2.length) + 4);
  });
  byCv.forEach((result, index) => {
    ctx.fillStyle = colorFor(result);
    ctx.textAlign = 'left';
    ctx.fillText(`${result.name} ${formatScore(result.cvRmse, 3)}`,
                 rightX + 6, rowY(index, byCv.length) + 4);
  });

  const disagree = byR2[0] !== byCv[0];
  caption(panel,
    disagree
      ? `R² prefers ${byR2[0].name}, cross-validation prefers ${byCv[0].name}. `
        + 'A crossing line is a model that looks better than it predicts.'
      : 'Both statistics agree on the winner here.',
    disagree ? 'alert small' : 'muted small');
}


// ---------------------------------------------------------------
// getting data in and results out
// ---------------------------------------------------------------

function connectDialogs() {
  const dataDialog = byId('dataDialog');
  byId('dataButton').addEventListener('click', () => {
    byId('csvMessage').textContent = '';
    byId('csvText').value = pointsAsText();
    dataDialog.showModal();
  });
  byId('csvCancel').addEventListener('click', () => dataDialog.close());
  byId('csvLoad').addEventListener('click', () => {
    const parsed = parseTable(byId('csvText').value);
    if (parsed.error !== null) {
      byId('csvMessage').className = 'small alert';
      byId('csvMessage').textContent = parsed.error;
      return;
    }
    remember();
    bridge.reset();
    points = parsed.points;
    selectedName = null;
    markActiveSample(-1);
    dataDialog.close();
    analyze();
    reframe();
  });
  byId('csvFile').addEventListener('change', async event => {
    const file = event.target.files[0];
    if (!file) return;
    byId('csvText').value = await file.text();
    byId('csvMessage').className = 'small muted';
    byId('csvMessage').textContent = `read ${file.name}`;
  });

  const helpDialog = byId('helpDialog');
  byId('helpButton').addEventListener('click', () => helpDialog.showModal());
  byId('helpClose').addEventListener('click', () => helpDialog.close());

  byId('shareButton').addEventListener('click', shareLink);
  byId('imageButton').addEventListener('click', saveImage);
}

function pointsAsText() {
  return points.map(p => `${trimNumber(p.x)}, ${trimNumber(p.y)}`).join('\n');
}

// accepts commas, tabs, semicolons or plain spaces, and skips a header
// row, because data copied out of a spreadsheet arrives in all of those
function parseTable(text) {
  const collected = [];
  const lines = text.split(/\r?\n/);
  let skipped = 0;
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed === '') continue;
    const parts = trimmed.split(/[,;\t]+|\s+/).filter(part => part !== '');
    if (parts.length < 2) { skipped++; continue; }
    const x = parseNumber(parts[0]);
    const y = parseNumber(parts[1]);
    if (x === null || y === null) { skipped++; continue; }
    collected.push({ x, y, excluded: false });
  }
  if (collected.length === 0) {
    return { points: [], error: 'No pairs of numbers found in that text.' };
  }
  if (skipped > 1) {
    return {
      points: collected,
      error: `Found ${collected.length} points, but ${skipped} lines did ` +
             'not look like a pair of numbers. Check the text, then press ' +
             'the button again to use them anyway.'
    };
  }
  return { points: collected, error: null };
}

// The dataset travels in the address itself, so a link is all somebody
// needs to see exactly what you are looking at. Nothing is uploaded.
function shareLink() {
  const packed = points.map(p =>
    `${trimNumber(p.x)}:${trimNumber(p.y)}${p.excluded ? 'x' : ''}`).join(',');
  const url = `${location.origin}${location.pathname}#d=${encodeURIComponent(packed)}`;
  navigator.clipboard.writeText(url).then(
    () => flashButton('shareButton', 'Link copied'),
    () => window.prompt('Copy this link:', url)
  );
}

function loadFromLink() {
  const match = location.hash.match(/d=([^&]+)/);
  if (!match) return false;
  const collected = [];
  for (const chunk of decodeURIComponent(match[1]).split(',')) {
    const excluded = chunk.endsWith('x');
    const [left, right] = (excluded ? chunk.slice(0, -1) : chunk).split(':');
    const x = parseNumber(left);
    const y = parseNumber(right);
    if (x === null || y === null) continue;
    collected.push({ x, y, excluded });
  }
  if (collected.length === 0) return false;
  points = collected;
  markActiveSample(-1);
  analyze();
  reframe();
  return true;
}

// the graph as a picture, for a lab report
function saveImage() {
  const source = byId('graph');
  // the canvas is transparent, so paint a white sheet behind it first
  const sheet = document.createElement('canvas');
  sheet.width = source.width;
  sheet.height = source.height;
  const ctx = sheet.getContext('2d');
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, sheet.width, sheet.height);
  ctx.drawImage(source, 0, 0);

  const link = document.createElement('a');
  link.download = 'verifit-graph.png';
  link.href = sheet.toDataURL('image/png');
  link.click();
  flashButton('imageButton', 'Saved');
}

function flashButton(id, message) {
  const button = byId(id);
  const original = button.textContent;
  button.textContent = message;
  setTimeout(() => { button.textContent = original; }, 1400);
}


boot();
