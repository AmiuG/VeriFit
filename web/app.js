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

let bridge = null;      // the python module, once it is loaded
let samples = [];       // the built in datasets, read from python
let points = [];        // whatever is currently being fitted
let latest = null;      // the most recent analysis


function show(id, isVisible) {
  document.getElementById(id).hidden = !isVisible;
}

function setBootStatus(message) {
  document.getElementById('bootStatus').textContent = message;
}

function reportFailure(error) {
  show('booting', false);
  show('failed', true);
  document.getElementById('failureText').textContent = String(error);
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
    setBootStatus('Downloading Python…');
    const pyodide = await loadPyodide();

    setBootStatus('Loading VeriFit…');
    pyodide.FS.mkdir('/verifit');
    // the website reads the maths straight out of src/, so there is
    // only ever one copy of it and it cannot drift from the app
    for (const name of PYTHON_MODULES) {
      const source = await fetchText(`src/${name}.py`);
      pyodide.FS.writeFile(`/verifit/${name}.py`, source);
    }
    pyodide.FS.writeFile('/verifit/bridge.py',
                         await fetchText('web/bridge.py'));

    pyodide.runPython("import sys; sys.path.insert(0, '/verifit')");
    bridge = pyodide.runPython('import bridge; bridge');

    samples = JSON.parse(bridge.samples());
    buildSampleButtons();
    loadSample(0);

    show('booting', false);
    show('app', true);
  } catch (error) {
    reportFailure(error);
  }
}


// ---------------------------------------------------------------
// asking python for an answer
// ---------------------------------------------------------------

function analyze() {
  latest = JSON.parse(bridge.analyze(JSON.stringify(points)));
  renderVerdict();
  renderWarnings();
  renderRanking();
  renderUnavailable();
  drawGraph();
}

function buildSampleButtons() {
  const holder = document.getElementById('sampleButtons');
  holder.innerHTML = '';
  samples.forEach((sample, index) => {
    const button = document.createElement('button');
    button.textContent = sample.label;
    button.title = sample.hint;
    button.addEventListener('click', () => loadSample(index));
    holder.appendChild(button);
  });
}

function loadSample(index) {
  // a fresh dataset forgets which curves were switched on, so the top
  // three show again, the same way the desktop app behaves
  bridge.reset();
  points = samples[index].points.map(p => ({ x: p.x, y: p.y }));
  const buttons = document.querySelectorAll('#sampleButtons button');
  buttons.forEach((button, i) => {
    button.classList.toggle('active', i === index);
  });
  analyze();
}


// ---------------------------------------------------------------
// putting the answer on the page
// ---------------------------------------------------------------

function formatScore(value, decimals = 4) {
  if (value === null || value === undefined) return 'n/a';
  if (value !== 0 && Math.abs(value) < 0.001) return value.toExponential(2);
  return value.toFixed(decimals);
}

function colorFor(result) {
  return CURVE_COLORS[result.colorIndex] || '#808080';
}

function renderVerdict() {
  const box = document.getElementById('verdict');
  box.textContent = latest.verdict;
  box.hidden = latest.verdict === '';
}

function renderWarnings() {
  const holder = document.getElementById('warnings');
  holder.innerHTML = '';
  for (const warning of latest.warnings) {
    const line = document.createElement('div');
    line.className = 'warning';
    line.textContent = warning;
    holder.appendChild(line);
  }
}

function renderRanking() {
  const list = document.getElementById('ranking');
  list.innerHTML = '';
  latest.results.forEach((result, index) => {
    const row = document.createElement('li');

    const swatch = document.createElement('span');
    swatch.className = 'swatch';
    swatch.style.background = result.isVisible ? colorFor(result)
                                               : 'transparent';
    swatch.style.border = `1px solid ${colorFor(result)}`;

    const rank = document.createElement('span');
    rank.className = 'rank';
    rank.textContent = `${index + 1}.`;

    const name = document.createElement('span');
    name.className = 'modelName';
    name.textContent = result.name;

    const score = document.createElement('span');
    score.className = 'score';
    score.textContent = formatScore(result.cvRmse);

    row.append(swatch, rank, name, score);
    row.title = result.equation;
    list.appendChild(row);
  });
}

function renderUnavailable() {
  const holder = document.getElementById('unavailable');
  if (latest.unavailable.length === 0) {
    holder.textContent = '';
    return;
  }
  const reasons = latest.unavailable
    .map(item => `${item.name}: ${item.reason}`)
    .join(' · ');
  holder.textContent = `not fitted — ${reasons}`;
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

function windowForPoints() {
  if (points.length === 0) return { xMin: 0, xMax: 10, yMin: 0, yMax: 10 };
  const xs = points.map(p => p.x);
  const ys = points.map(p => p.y);
  const [xMin, xMax] = padRange(Math.min(...xs), Math.max(...xs));
  const [yMin, yMax] = padRange(Math.min(...ys), Math.max(...ys));
  return { xMin, xMax, yMin, yMax };
}

function drawGraph() {
  const canvas = document.getElementById('graph');
  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;
  const pad = { left: 46, right: 14, top: 14, bottom: 30 };
  const view = windowForPoints();

  const toX = x => pad.left + (x - view.xMin) / (view.xMax - view.xMin)
                   * (width - pad.left - pad.right);
  const toY = y => height - pad.bottom - (y - view.yMin)
                   / (view.yMax - view.yMin) * (height - pad.top - pad.bottom);

  ctx.clearRect(0, 0, width, height);

  // grid and axis labels, laid out the way desmos does it
  ctx.font = '11px Ubuntu, sans-serif';
  ctx.fillStyle = '#5f5f5f';
  ctx.strokeStyle = '#e6e6e6';
  ctx.lineWidth = 1;
  for (const x of niceTicks(view.xMin, view.xMax)) {
    const px = Math.round(toX(x)) + 0.5;
    ctx.beginPath();
    ctx.moveTo(px, pad.top);
    ctx.lineTo(px, height - pad.bottom);
    ctx.stroke();
    ctx.textAlign = 'center';
    ctx.fillText(trimNumber(x), px, height - pad.bottom + 15);
  }
  for (const y of niceTicks(view.yMin, view.yMax)) {
    const py = Math.round(toY(y)) + 0.5;
    ctx.beginPath();
    ctx.moveTo(pad.left, py);
    ctx.lineTo(width - pad.right, py);
    ctx.stroke();
    ctx.textAlign = 'right';
    ctx.fillText(trimNumber(y), pad.left - 6, py + 4);
  }

  // the curves, asked for one at a time so python keeps ownership of
  // where each model can and cannot be drawn
  if (latest) {
    for (const result of latest.results) {
      if (!result.isVisible) continue;
      const pieces = JSON.parse(
        bridge.curve(result.name, view.xMin, view.xMax, 240));
      ctx.strokeStyle = colorFor(result);
      ctx.lineWidth = 2;
      for (const piece of pieces) {
        ctx.beginPath();
        piece.forEach(([x, y], i) => {
          const px = toX(x);
          const py = toY(y);
          if (i === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        });
        ctx.stroke();
      }
    }
  }

  // the data itself goes on top of the curves
  ctx.fillStyle = '#000';
  for (const point of points) {
    ctx.beginPath();
    ctx.arc(toX(point.x), toY(point.y), 4, 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.strokeStyle = '#cdcdcd';
  ctx.strokeRect(pad.left + 0.5, pad.top + 0.5,
                 width - pad.left - pad.right - 1,
                 height - pad.top - pad.bottom - 1);
}

// round tick positions, the same 1 / 2 / 5 rule graphview.py uses
function niceTicks(low, high, target = 8) {
  if (high <= low) return [];
  const rough = (high - low) / target;
  const power = Math.floor(Math.log10(rough));
  const base = Math.pow(10, power);
  let step = 10 * base;
  for (const multiple of [1, 2, 5]) {
    if (rough <= multiple * base) { step = multiple * base; break; }
  }
  const ticks = [];
  for (let i = Math.ceil(low / step); i <= Math.floor(high / step); i++) {
    ticks.push(i * step);
  }
  return ticks;
}

function trimNumber(value) {
  const rounded = Math.round(value * 1000) / 1000;
  return String(rounded);
}


boot();
