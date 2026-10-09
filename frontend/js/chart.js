/**
 * A small SVG line chart.
 *
 * Built by hand rather than pulled from a chart library so the marks,
 * the theme tokens and the crosshair behave exactly like the rest of
 * the app — and so the page carries no charting dependency.
 */

import { el, formatNumber } from './ui.js';

const SVG_NS = 'http://www.w3.org/2000/svg';

function svg(tag, attrs = {}) {
  const node = document.createElementNS(SVG_NS, tag);

  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined) continue;
    node.setAttribute(key, String(value));
  }

  return node;
}

/** Axis ticks on 1/2/5×10^n steps so labels stay round. */
function niceTicks(min, max, count = 6) {
  if (!Number.isFinite(min) || !Number.isFinite(max)) return [];

  if (min === max) {
    const pad = Math.abs(min) || 1;
    min -= pad / 2;
    max += pad / 2;
  }

  const rawStep = (max - min) / count;
  const magnitude = 10 ** Math.floor(Math.log10(rawStep));
  const normalised = rawStep / magnitude;

  const step =
    (normalised >= 5 ? 5 : normalised >= 2 ? 2 : 1) * magnitude;

  const ticks = [];

  for (
    let value = Math.ceil(min / step) * step;
    value <= max + step / 1e6;
    value += step
  ) {
    ticks.push(Number(value.toFixed(12)));
  }

  return ticks;
}

/**
 * @param {object} options
 * @param {number[]} options.x         shared x values
 * @param {{name:string, values:(number|null)[], color:string}[]} options.series
 * @param {string} options.xLabel
 * @param {string} options.yLabel
 */
export function lineChart({ x, series, xLabel = 'x', yLabel = 'f(x)' }) {
  const width = 760;
  const height = 340;
  const margin = { top: 14, right: 16, bottom: 38, left: 56 };

  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;

  const finite = [];

  for (const line of series) {
    for (const value of line.values) {
      if (typeof value === 'number' && Number.isFinite(value)) finite.push(value);
    }
  }

  const xMin = Math.min(...x);
  const xMax = Math.max(...x);

  let yMin = finite.length ? Math.min(...finite) : -1;
  let yMax = finite.length ? Math.max(...finite) : 1;

  if (yMin === yMax) {
    const pad = Math.abs(yMin) || 1;
    yMin -= pad;
    yMax += pad;
  } else {
    const pad = (yMax - yMin) * 0.08;
    yMin -= pad;
    yMax += pad;
  }

  const sx = (value) =>
    margin.left + ((value - xMin) / (xMax - xMin || 1)) * plotWidth;
  const sy = (value) =>
    margin.top + plotHeight - ((value - yMin) / (yMax - yMin || 1)) * plotHeight;

  const root = svg('svg', {
    viewBox: `0 0 ${width} ${height}`,
    role: 'img',
    'aria-label': `${yLabel} against ${xLabel}`,
    preserveAspectRatio: 'xMidYMid meet'
  });

  // --- grid + axes (recessive) ---------------------------------
  const grid = svg('g', { class: 'chart-grid' });
  const axis = svg('g', { class: 'chart-axis' });

  for (const tick of niceTicks(yMin, yMax, 5)) {
    if (tick < yMin || tick > yMax) continue;

    const y = sy(tick);
    grid.append(svg('line', { x1: margin.left, x2: width - margin.right, y1: y, y2: y }));

    const label = svg('text', {
      x: margin.left - 9,
      y: y + 4,
      'text-anchor': 'end'
    });
    label.textContent = formatNumber(tick, 4);
    axis.append(label);
  }

  for (const tick of niceTicks(xMin, xMax, 6)) {
    if (tick < xMin || tick > xMax) continue;

    const xPosition = sx(tick);
    const label = svg('text', {
      x: xPosition,
      y: height - margin.bottom + 19,
      'text-anchor': 'middle'
    });
    label.textContent = formatNumber(tick, 4);
    axis.append(label);
  }

  // Zero lines help far more than extra gridlines on a Fourier plot.
  if (yMin < 0 && yMax > 0) {
    axis.append(svg('line', {
      x1: margin.left, x2: width - margin.right, y1: sy(0), y2: sy(0)
    }));
  }
  if (xMin < 0 && xMax > 0) {
    axis.append(svg('line', {
      x1: sx(0), x2: sx(0), y1: margin.top, y2: margin.top + plotHeight
    }));
  }

  const xTitle = svg('text', {
    x: margin.left + plotWidth / 2,
    y: height - 4,
    'text-anchor': 'middle'
  });
  xTitle.textContent = xLabel;
  axis.append(xTitle);

  root.append(grid, axis);

  // --- series --------------------------------------------------
  for (const line of series) {
    let path = '';
    let pen = false;

    line.values.forEach((value, index) => {
      if (typeof value !== 'number' || !Number.isFinite(value)) {
        pen = false;
        return;
      }

      const command = pen ? 'L' : 'M';
      path += `${command}${sx(x[index]).toFixed(2)},${sy(value).toFixed(2)}`;
      pen = true;
    });

    if (path) {
      root.append(svg('path', {
        d: path,
        class: 'chart-series',
        stroke: line.color
      }));
    }
  }

  // --- crosshair + tooltip ------------------------------------
  const crosshair = svg('line', {
    y1: margin.top,
    y2: margin.top + plotHeight,
    stroke: 'currentColor',
    'stroke-width': 1,
    'stroke-dasharray': '3 3',
    opacity: 0
  });
  crosshair.style.color = 'var(--text-3)';

  const markers = series.map((line) => {
    const dot = svg('circle', {
      r: 4.5,
      fill: line.color,
      stroke: 'var(--surface)',
      'stroke-width': 2,
      opacity: 0
    });
    root.append(dot);
    return dot;
  });

  root.append(crosshair);

  const tip = el('div', { class: 'chart-tip' });
  tip.hidden = true;

  const wrap = el('div', { class: 'chart-wrap' }, [root, tip]);

  function hide() {
    crosshair.setAttribute('opacity', 0);
    markers.forEach((dot) => dot.setAttribute('opacity', 0));
    tip.hidden = true;
  }

  function move(event) {
    const box = root.getBoundingClientRect();
    if (!box.width) return;

    const scale = width / box.width;
    const pointerX = (event.clientX - box.left) * scale;

    const ratio = (pointerX - margin.left) / (plotWidth || 1);
    let index = Math.round(ratio * (x.length - 1));
    index = Math.max(0, Math.min(x.length - 1, index));

    crosshair.setAttribute('x1', sx(x[index]));
    crosshair.setAttribute('x2', sx(x[index]));
    crosshair.setAttribute('opacity', 1);

    const rows = [el('div', { class: 'tip-row', text: `${xLabel} = ${formatNumber(x[index], 4)}` })];

    series.forEach((line, seriesIndex) => {
      const value = line.values[index];
      const dot = markers[seriesIndex];

      if (typeof value === 'number' && Number.isFinite(value)) {
        dot.setAttribute('cx', sx(x[index]));
        dot.setAttribute('cy', sy(value));
        dot.setAttribute('opacity', 1);
      } else {
        dot.setAttribute('opacity', 0);
      }

      const swatch = el('span', { class: 'swatch' });
      swatch.style.background = line.color;
      swatch.style.setProperty('--series-color', line.color);

      rows.push(el('div', { class: 'tip-row' }, [
        swatch,
        `${line.name}: ${formatNumber(value, 5)}`
      ]));
    });

    tip.replaceChildren(...rows);
    tip.hidden = false;
    tip.style.left = `${(sx(x[index]) / width) * 100}%`;
    tip.style.top = `${(margin.top / height) * 100}%`;
  }

  root.addEventListener('pointermove', move);
  root.addEventListener('pointerleave', hide);

  // --- legend (always present for two or more series) ----------
  const legend = el('div', { class: 'chart-legend' },
    series.map((line) => {
      const swatch = el('span', { class: 'swatch' });
      swatch.style.background = line.color;
      swatch.style.setProperty('--series-color', line.color);
      return el('span', { class: 'key' }, [swatch, line.name]);
    })
  );

  return el('div', {}, [wrap, legend]);
}

/** Read a themed colour token at call time so dark mode stays correct. */
export function token(name) {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim() || '#2a78d6';
}
