
const M = DATA, U = UI_TEXT;
// boards in the ink colours of the record's profile (graph.py board_colours)
const BOARD_COLOR = {...M.board_colours, records:'#7a4fa0', sources:'#8a8a84'};
const GROUP_COLOR = {thesis:'#7a4fa0', hypothesis:'#c0392b', qualification:'#d68910', ontology:'#1f8a9a', source:'#8a8a84'};
const EDGE_COLOR = {flow:'#1f77b4', shift:'#d62728', opposes:'#ff7f0e', produces:'#2ca02c', uses:'#17becf',
  belongs:'#8c564b', represents:'#9467bd', refers:'#a3a39c', other:'#7f7f7f', in:'#bcbd22', transition:'#e377c2',
  tests:'#c0392b', qualifies:'#d68910', feeds:'#7a4fa0', valid_for:'#1f8a9a', cooperation:'#1f8a9a',
  tested_by:'#c0392b', cites:'#c9c7c0'};
// relation kinds a profile adds (graph.py edge_kinds) are drawn grey
const edgeColor = k => EDGE_COLOR[k] || '#7f7f7f';
const CAMERA = 2600;
// height of each plane: the boards, records above, sources below (graph.py planes, LAYER)
const PLANE_Z = M.planes;
const DASHED = new Set(['tests','qualifies','feeds','valid_for','cooperation','tested_by','cites','in']);
const byId = new Map(M.nodes.map(n => [n.id, n]));
const out = new Map(), inc = new Map();
M.nodes.forEach(n => { out.set(n.id, []); inc.set(n.id, []); });
M.edges.forEach(e => { out.get(e.s).push(e); inc.get(e.t).push(e); });
M.nodes.forEach(n => { n.deg = out.get(n.id).length + inc.get(n.id).length; });

const state = {
  boards: Object.fromEntries(Object.keys(M.boards).map(b => [b, true])), records: true, sources: false,
  kinds: Object.fromEntries(Object.keys(M.edge_kinds).map(k => [k, k !== 'cites'])),
  yaw: -0.6, pitch: 0.55, zoom: 0.42, panX: 0, panY: 0,
  sel: null, hover: null, depth2: false, allLabels: false, query: ''
};

function nodeVisible(n) {
  if (n.g === 'element') return state.boards[n.b];
  if (n.g === 'source') return state.sources;
  return state.records;
}
function edgeVisible(e) {
  return state.kinds[e.k] && nodeVisible(byId.get(e.s)) && nodeVisible(byId.get(e.t));
}

// ---------- panel ----------
const el = (tag, attrs = {}, ...kids) => {
  const x = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'on') for (const [ev, f] of Object.entries(v)) x.addEventListener(ev, f);
    else if (k === 'html') x.innerHTML = v; else x.setAttribute(k, v);
  }
  kids.flat().forEach(c => x.append(c instanceof Node ? c : document.createTextNode(c)));
  return x;
};
function check(label, get, set, swatch) {
  const box = el('input', {type: 'checkbox'});
  box.checked = get();
  box.addEventListener('change', () => { set(box.checked); draw(); });
  return el('label', {}, box, swatch || '', label);
}
const left = document.getElementById('controls');
function buildControls() {
  left.innerHTML = '';
  left.append(el('input', {type: 'search', placeholder: U.search, on: {input: ev => { state.query = ev.target.value.trim().toLowerCase(); findQuery(); draw(); }}}));
  left.append(el('h2', {}, U.views));
  const views = [[U.all, () => setKinds(k => k !== 'cites')], [U.flows, () => setKinds(k => M.flow_kinds.includes(k))],
    [U.hyp, () => { state.records = true; setKinds(k => k === 'tests' || k === 'tested_by'); }]];
  views.forEach(([t, f]) => left.append(el('button', {on: {click: () => { f(); buildControls(); draw(); }}}, t)));
  left.append(el('br'));
  [[U.tilt, 0.55], [U.top, 1.5], [U.side, 0.02]].forEach(([t, p]) =>
    left.append(el('button', {on: {click: () => { state.pitch = p; draw(); }}}, t)));
  left.append(el('h2', {}, U.boards));
  for (const [b, name] of Object.entries(M.boards))
    left.append(check(name, () => state.boards[b], v => state.boards[b] = v, el('span', {class: 'dot', style: `background:${BOARD_COLOR[b]}`})));
  left.append(el('h2', {}, U.layers));
  left.append(check(U.records, () => state.records, v => state.records = v, el('span', {class: 'dot', style: `background:${BOARD_COLOR.records}`})));
  left.append(check(U.sources, () => state.sources, v => { state.sources = v; if (v) state.kinds.cites = true; buildControls(); }, el('span', {class: 'dot', style: `background:${BOARD_COLOR.sources}`})));
  left.append(check(U.depth, () => state.depth2, v => state.depth2 = v));
  left.append(check(U.labels, () => state.allLabels, v => state.allLabels = v));
  left.append(el('h2', {}, U.edges));
  const counts = {};
  M.edges.forEach(e => counts[e.k] = (counts[e.k] || 0) + 1);
  for (const [k, name] of Object.entries(M.edge_kinds)) {
    if (!counts[k]) continue;
    left.append(check(`${name} (${counts[k]})`, () => state.kinds[k], v => state.kinds[k] = v,
      el('span', {class: 'sw', style: `background:${edgeColor(k)}`})));
  }
  left.append(el('p', {class: 'help'}, U.help));
}
function setKinds(pred) { for (const k of Object.keys(state.kinds)) state.kinds[k] = pred(k); }

function findQuery() {
  if (!state.query) return;
  const hit = M.nodes.find(n => nodeVisible(n) && (n.id.toLowerCase() === state.query))
    || M.nodes.find(n => nodeVisible(n) && (n.id.toLowerCase().includes(state.query) || n.label.toLowerCase().includes(state.query)));
  if (hit) select(hit.id);
}

const info = document.getElementById('info');
function link(id) {
  const n = byId.get(id);
  return el('a', {class: 'n', on: {click: () => select(id)}}, n ? `${n.short}` : id);
}
function select(id) {
  state.sel = id;
  const n = byId.get(id);
  if (!nodeVisible(n)) { if (n.g === 'element') state.boards[n.b] = true; else if (n.g === 'source') state.sources = true; else state.records = true; buildControls(); }
  info.innerHTML = '';
  const where = n.g === 'element' ? M.boards[n.b] : n.kind;
  info.append(el('div', {class: 'id'}, n.id), el('h3', {}, n.label));
  // fixed values by their words in the language (graph.py _words); the ids stay in n.status, n.voice, n.epistemic
  const w = n.words || {status: n.status, voice: n.voice, epistemic: n.epistemic};
  const meta = [where, n.g === 'element' ? n.kind : '', w.status ? `${U.status}: ${w.status}` : '', w.voice ? `${U.voice}: ${w.voice}` : '', w.epistemic || ''].filter(Boolean).join(' · ');
  info.append(el('div', {class: 'meta'}, meta));
  // only web links become anchors; any other scheme (javascript:, data:) stays plain text
  if (n.url) info.append(el('div', {class: 'meta'}, /^https?:\/\//i.test(n.url)
    ? el('a', {href: n.url, target: '_blank', rel: 'noopener noreferrer'}, n.url) : n.url));
  if (n.note) info.append(el('div', {class: 'note'}, n.note));
  if (n.extra) for (const [k, v] of Object.entries(n.extra)) info.append(el('div', {class: 'note'}, `${M.extra_labels[k] || k}: ${v}`));
  if (n.fillers && n.fillers.length) info.append(el('div', {class: 'meta'}, `${U.fillers}: ${n.fillers.join('; ')}`));
  if (n.detail) {
    const t = el('table');
    if (n.detail.title) info.append(el('div', {class: 'meta'}, n.detail.title));
    t.append(el('tr', {}, n.detail.columns.map(c => el('th', {}, c))));
    n.detail.rows.forEach(r => t.append(el('tr', {}, r.map(c => el('td', {}, c)))));
    info.append(t);
  }
  const group = (list, side) => {
    const by = {};
    list.forEach(e => (by[e.k] = by[e.k] || []).push(e));
    for (const [k, es] of Object.entries(by)) {
      info.append(el('div', {class: 'meta'}, `${M.edge_kinds[k]} — ${side}`));
      info.append(el('ul', {}, es.map(e => el('li', {}, link(side === U.out ? e.t : e.s), e.l ? ` — ${e.l}` : '', e.c ? [' · ', el('b', {}, e.c)] : ''))));
    }
  };
  group(out.get(id), U.out);
  group(inc.get(id), U.inc);
  draw();
}

// ---------- 3D ----------
const canvas = document.getElementById('c'), ctx = canvas.getContext('2d');
const tip = document.getElementById('tip');
let W = 0, H = 0, proj = new Map();
function resize() {
  const r = canvas.parentElement.getBoundingClientRect(), d = window.devicePixelRatio || 1;
  W = r.width; H = r.height; canvas.width = W * d; canvas.height = H * d;
  ctx.setTransform(d, 0, 0, d, 0, 0); draw();
}
function project(x, y, z) {
  // world: x right, y depth on the board, z up between planes
  const cy = Math.cos(state.yaw), sy = Math.sin(state.yaw), cp = Math.cos(state.pitch), sp = Math.sin(state.pitch);
  const x1 = x * cy - y * sy, y1 = x * sy + y * cy;
  // pitch 0: looking along the planes; pitch pi/2: looking straight down
  const yv = y1 * sp - z * cp;
  const toward = z * sp - y1 * cp;  // positive = closer to the viewer
  const f = CAMERA / Math.max(300, CAMERA - toward);
  return {x: W / 2 + state.panX + x1 * f * state.zoom, y: H / 2 + state.panY + yv * f * state.zoom, d: toward, f};
}
function neighbours() {
  const keep = new Set();
  if (!state.sel) return null;
  keep.add(state.sel);
  const step = ids => { const next = []; ids.forEach(i => { out.get(i).concat(inc.get(i)).forEach(e => { if (!edgeVisible(e)) return; const o = e.s === i ? e.t : e.s; if (!keep.has(o)) { keep.add(o); next.push(o); } }); }); return next; };
  const first = step([state.sel]);
  if (state.depth2) step(first);
  return keep;
}
function planeCorners(z) {
  const h = 560;
  return [[-h, -h], [h, -h], [h, h], [-h, h]].map(([x, y]) => project(x, y, z));
}
function draw() {
  if (!W) return;
  ctx.clearRect(0, 0, W, H);
  const planes = [['records', state.records], ...Object.keys(M.boards).map(b => [b, state.boards[b]]), ['sources', state.sources]];
  planes.forEach(([b, on]) => {
    if (!on) return;
    const z = PLANE_Z[b];
    const c = planeCorners(z);
    ctx.beginPath(); c.forEach((p, i) => i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)); ctx.closePath();
    ctx.fillStyle = BOARD_COLOR[b] + '10'; ctx.fill(); ctx.strokeStyle = BOARD_COLOR[b] + '55'; ctx.stroke();
    ctx.fillStyle = BOARD_COLOR[b]; ctx.font = '600 12px sans-serif';
    ctx.fillText((M.board_shorts || M.boards)[b] || (b === 'records' ? U.records : U.sources), c[0].x + 6, c[0].y - 6);
  });
  proj = new Map();
  M.nodes.forEach(n => { if (nodeVisible(n)) proj.set(n.id, project(n.x, n.y, n.z)); });
  const keep = neighbours();
  M.edges.forEach(e => {
    if (!edgeVisible(e)) return;
    const a = proj.get(e.s), b = proj.get(e.t);
    const lit = !keep || (keep.has(e.s) && keep.has(e.t) && (e.s === state.sel || e.t === state.sel || state.depth2));
    ctx.strokeStyle = edgeColor(e.k) + (lit ? (keep ? 'ee' : (DASHED.has(e.k) ? '30' : '88')) : '18');
    ctx.lineWidth = lit && keep ? 2 : 1;
    ctx.setLineDash(DASHED.has(e.k) ? [4, 3] : []);
    ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
    if (lit && keep) { // arrow head
      const ang = Math.atan2(b.y - a.y, b.x - a.x), r = 7;
      ctx.setLineDash([]); ctx.beginPath();
      ctx.moveTo(b.x - 6 * Math.cos(ang), b.y - 6 * Math.sin(ang));
      ctx.lineTo(b.x - (6 + r) * Math.cos(ang - 0.4), b.y - (6 + r) * Math.sin(ang - 0.4));
      ctx.lineTo(b.x - (6 + r) * Math.cos(ang + 0.4), b.y - (6 + r) * Math.sin(ang + 0.4));
      ctx.closePath(); ctx.fillStyle = edgeColor(e.k); ctx.fill();
    }
    if (lit && keep && e.c) { // what a flow carries, written on the link
      ctx.font = '600 11px sans-serif'; ctx.textAlign = 'center';
      const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2, w = ctx.measureText(e.c).width;
      ctx.fillStyle = '#ffffffdd'; ctx.fillRect(mx - w / 2 - 2, my - 11, w + 4, 14);
      ctx.fillStyle = edgeColor(e.k); ctx.fillText(e.c, mx, my);
      ctx.textAlign = 'start';
    }
  });
  ctx.setLineDash([]);
  const order = [...proj.entries()].sort((p, q) => p[1].d - q[1].d);
  order.forEach(([id, p]) => {
    const n = byId.get(id), lit = !keep || keep.has(id);
    const r = (3 + Math.sqrt(n.deg) * 1.4) * Math.max(0.6, p.f);
    ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, 7);
    const col = n.g === 'element' ? BOARD_COLOR[n.b] : GROUP_COLOR[n.g];
    ctx.fillStyle = col + (lit ? 'ff' : '30'); ctx.fill();
    if (n.epistemic === 'hypothesis' || n.epistemic === 'unverified') { ctx.strokeStyle = '#fff'; ctx.lineWidth = 1; ctx.stroke(); }
    if (id === state.sel || id === state.hover) { ctx.strokeStyle = '#1d1d1b'; ctx.lineWidth = 2; ctx.stroke(); }
    const showLabel = id === state.sel || id === state.hover || (keep && keep.has(id)) || state.allLabels || (!keep && n.g !== 'element' && n.g !== 'source');
    if (showLabel) {
      ctx.font = (id === state.sel ? '600 ' : '') + '12px sans-serif';
      ctx.fillStyle = lit ? '#1d1d1b' : '#1d1d1b55';
      ctx.fillText(n.short, p.x + r + 3, p.y + 4);
    }
  });
}
function pick(mx, my) {
  let best = null, bd = 12;
  proj.forEach((p, id) => { const d = Math.hypot(p.x - mx, p.y - my); if (d < bd) { bd = d; best = id; } });
  return best;
}
let drag = null;
canvas.addEventListener('contextmenu', e => e.preventDefault());
canvas.addEventListener('pointerdown', e => { drag = {x: e.clientX, y: e.clientY, pan: e.shiftKey || e.button === 2, moved: false}; canvas.setPointerCapture(e.pointerId); });
canvas.addEventListener('pointermove', e => {
  const r = canvas.getBoundingClientRect();
  if (drag) {
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    if (Math.abs(dx) + Math.abs(dy) > 2) drag.moved = true;
    if (drag.pan) { state.panX += dx; state.panY += dy; }
    else { state.yaw += dx * 0.006; state.pitch = Math.max(0.02, Math.min(1.55, state.pitch + dy * 0.006)); }
    drag.x = e.clientX; drag.y = e.clientY; draw(); return;
  }
  const id = pick(e.clientX - r.left, e.clientY - r.top);
  if (id !== state.hover) { state.hover = id; draw(); }
  if (id) { const n = byId.get(id); tip.style.display = 'block'; tip.textContent = `${n.id}: ${n.label}`;
    tip.style.left = (e.clientX - r.left + 14) + 'px'; tip.style.top = (e.clientY - r.top + 10) + 'px'; }
  else tip.style.display = 'none';
});
canvas.addEventListener('pointerup', e => {
  const r = canvas.getBoundingClientRect();
  if (drag && !drag.moved) { const id = pick(e.clientX - r.left, e.clientY - r.top); if (id) select(id); else { state.sel = null; info.innerHTML = `<p class="help">${U.pick}</p>`; draw(); } }
  drag = null;
});
canvas.addEventListener('wheel', e => { e.preventDefault(); state.zoom = Math.max(0.08, Math.min(4, state.zoom * (e.deltaY > 0 ? 0.9 : 1.1))); draw(); }, {passive: false});
window.addEventListener('resize', resize);
buildControls();
info.innerHTML = `<p class="help">${U.pick}</p>`;
resize();
