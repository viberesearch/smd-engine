(function () {
  'use strict';
  var cfg = JSON.parse(document.getElementById('cfg').textContent);
  var ui = cfg.ui;
  var form = document.getElementById('f');
  var KEY = 'smdtask:' + cfg.mode + ':' + cfg.key;

  function all(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }
  function q(s) {
    return JSON.stringify(String(s)).split(String.fromCharCode(8232)).join('\\u2028').split(String.fromCharCode(8233)).join('\\u2029');
  }
  function flow(list) {
    return '[' + list.map(function (x) { return typeof x === 'number' ? String(x) : q(x); }).join(', ') + ']';
  }
  function field(k) {
    var el = form.querySelector('[data-s="' + k + '"]');
    return el ? el.value : '';
  }
  function checked(k) {
    return all('[data-s="' + k + '"]', form)
      .filter(function (e) { return e.checked; })
      .map(function (e) { return e.value; });
  }
  function say(msg, kind) {
    var box = document.getElementById('status');
    box.textContent = msg;
    box.className = kind || '';
  }
  function el(tag, attrs, kids) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (a) { node.setAttribute(a, attrs[a]); });
    (kids || []).forEach(function (k) {
      node.appendChild(typeof k === 'string' ? document.createTextNode(k) : k);
    });
    return node;
  }

  // tabs
  function show(name) {
    all('section.tab').forEach(function (s) { s.classList.toggle('on', s.id === 'tab-' + name); });
    all('nav.tabs button').forEach(function (b) { b.classList.toggle('on', b.getAttribute('data-tab') === name); });
  }
  all('nav.tabs button').forEach(function (b) {
    b.addEventListener('click', function () { show(b.getAttribute('data-tab')); });
  });
  show(all('nav.tabs button')[0].getAttribute('data-tab'));

  // rows that the member adds: transcripts, added points
  function rowValues(row) {
    var o = {};
    all('[data-r]', row).forEach(function (e) { o[e.getAttribute('data-r')] = e.value; });
    if (row.getAttribute('data-sha')) { o.sha256 = row.getAttribute('data-sha'); }
    return o;
  }
  function rowsOf(kind) {
    return all('.row', document.querySelector('[data-rows="' + kind + '"]')).map(rowValues);
  }
  function sha256Of(file, done) {
    if (!(window.crypto && window.crypto.subtle)) { done(null); return; }
    var reader = new FileReader();
    reader.onload = function () {
      window.crypto.subtle.digest('SHA-256', reader.result).then(function (buf) {
        done(Array.prototype.map.call(new Uint8Array(buf), function (b) {
          return ('0' + b.toString(16)).slice(-2);
        }).join(''));
      }, function () { done(null); });
    };
    reader.onerror = function () { done(null); };
    reader.readAsArrayBuffer(file);
  }
  function addRow(kind, vals) {
    vals = vals || {};
    var box = document.querySelector('[data-rows="' + kind + '"]');
    var row = el('div', { 'class': 'row' + (kind === 'added' ? ' added' : '') });
    var drop = el('button', { type: 'button', 'class': 'link' }, [ui.remove]);
    drop.addEventListener('click', function () { row.remove(); save(); });
    if (kind === 'transcripts') {
      var path = el('input', { type: 'text', 'data-r': 'path', placeholder: ui.transcript_path });
      var note = el('input', { type: 'text', 'data-r': 'note', placeholder: ui.transcript_note });
      var pick = el('input', { type: 'file' });
      var sha = el('div', { 'class': 'sha' });
      path.value = vals.path || '';
      note.value = vals.note || '';
      if (vals.sha256) { row.setAttribute('data-sha', vals.sha256); sha.textContent = vals.sha256; }
      pick.addEventListener('change', function () {
        var file = pick.files[0];
        if (!file) { return; }
        if (!path.value) { path.value = file.name; }
        sha256Of(file, function (hex) {
          if (hex) { row.setAttribute('data-sha', hex); sha.textContent = hex; } else { row.removeAttribute('data-sha'); sha.textContent = ''; }
          save();
        });
      });
      row.appendChild(el('div', {}, [path, pick, sha]));
      row.appendChild(note);
    } else {
      var text = el('textarea', { 'data-r': 'text', placeholder: ui.added_text });
      var refs = el('input', { type: 'text', 'data-r': 'refs', placeholder: ui.added_refs });
      text.value = vals.text || '';
      refs.value = vals.refs || '';
      row.appendChild(text);
      row.appendChild(refs);
    }
    row.appendChild(drop);
    box.appendChild(row);
  }
  all('[data-add]').forEach(function (b) {
    b.addEventListener('click', function () { addRow(b.getAttribute('data-add')); save(); });
  });

  // autosave in this browser
  function save() {
    var st = { f: {}, rows: {} };
    all('[data-s]', form).forEach(function (e) {
      var k = e.getAttribute('data-s');
      if (e.type === 'radio' || e.type === 'checkbox') {
        if (e.checked) { (st.f[k] = st.f[k] || []).push(e.value); }
      } else { st.f[k] = e.value; }
    });
    all('[data-rows]').forEach(function (box) {
      st.rows[box.getAttribute('data-rows')] = all('.row', box).map(rowValues);
    });
    try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) { /* private mode */ }
  }
  function restore() {
    var raw = null;
    try { raw = localStorage.getItem(KEY); } catch (e) { return; }
    if (!raw) { return; }
    var st = JSON.parse(raw);
    all('[data-s]', form).forEach(function (e) {
      var k = e.getAttribute('data-s');
      var v = st.f[k];
      if (e.type === 'radio' || e.type === 'checkbox') { e.checked = !!v && v.indexOf(e.value) >= 0; }
      else if (typeof v === 'string') { e.value = v; }
    });
    Object.keys(st.rows || {}).forEach(function (kind) {
      st.rows[kind].forEach(function (v) { addRow(kind, v); });
    });
  }
  form.addEventListener('input', save);
  form.addEventListener('change', save);
  restore();
  var dateField = form.querySelector('[data-s="date"]');
  if (dateField && !dateField.value) {
    var d = new Date();
    dateField.value = d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2);
  }
  var counted = document.getElementById('count');
  all('[data-clear]').forEach(function (b) {
    b.addEventListener('click', function () {
      all('[data-s="' + b.getAttribute('data-clear') + '"]', form).forEach(function (e) { e.checked = false; });
      save();
      countAnswered();
    });
  });

  function download(name, text) {
    var blob = new Blob([text], { type: 'text/yaml;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 0);
  }

  // answers (mode pack)
  function value(it) {
    var k = 'v:' + it.id;
    if (it.kind === 'choice') { var c = checked(k); return c.length ? c[0] : null; }
    if (it.kind === 'multi' || it.kind === 'ids') { var m = checked(k); return m.length ? m : null; }
    var raw = field(k).trim();
    if (!raw) { return null; }
    if (it.kind === 'number') { var n = Number(raw.replace(',', '.')); return isNaN(n) ? null : n; }
    if (it.kind === 'steps') {
      var steps = raw.split(/\r?\n/).map(function (s) { return s.trim(); }).filter(Boolean);
      return steps.length ? steps : null;
    }
    return raw;
  }
  function answersYaml() {
    var P = cfg.pack, L = [];
    L.push('record: "task_answers"', 'schema_version: "0.1"');
    L.push('pack: {id: ' + q(P.id) + ', version: ' + q(P.version) + ', sha256: ' + q(P.sha256) + '}');
    L.push('member: ' + q(field('member')), 'date: ' + q(field('date')), 'drafted_by: ' + q(field('drafted')));
    var tr = rowsOf('transcripts').filter(function (r) { return r.path && r.path.trim(); });
    if (tr.length) {
      L.push('transcripts:');
      tr.forEach(function (r) {
        var f = ['path: ' + q(r.path.trim())];
        if (r.sha256) { f.push('sha256: ' + q(r.sha256)); }
        if (r.note && r.note.trim()) { f.push('note: ' + q(r.note.trim())); }
        L.push('  - {' + f.join(', ') + '}');
      });
    }
    var tc = cfg.term.filter(function (id) { return field('tc:' + id).trim(); });
    if (tc.length) {
      L.push('term_check:');
      tc.forEach(function (id) { L.push('  ' + q(id) + ': ' + q(field('tc:' + id).trim())); });
    } else { L.push('term_check: {}'); }
    var done = [];
    cfg.items.forEach(function (it) { var v = value(it); if (v !== null) { done.push([it, v]); } });
    if (done.length) {
      L.push('answers:');
      done.forEach(function (d) {
        var it = d[0], v = d[1];
        L.push('  ' + q(it.id) + ':');
        L.push('    value: ' + (Array.isArray(v) ? flow(v) : typeof v === 'number' ? String(v) : q(v)));
        [['r', 'reason'], ['s', 'source'], ['t', 'term_note']].forEach(function (p) {
          var t = field(p[0] + ':' + it.id).trim();
          if (t) { L.push('    ' + p[1] + ': ' + q(t)); }
        });
        var conf = field('c:' + it.id);
        if (conf) { L.push('    confidence: ' + q(conf)); }
      });
    } else { L.push('answers: {}'); }
    var added = rowsOf('added').filter(function (r) { return r.text && r.text.trim(); });
    if (added.length) {
      L.push('added:');
      added.forEach(function (r) {
        var refs = (r.refs || '').split(/[\s,;]+/).filter(Boolean);
        L.push('  - {text: ' + q(r.text.trim()) + (refs.length ? ', refs: ' + flow(refs) : '') + '}');
      });
    }
    return L.join('\n') + '\n';
  }
  function countAnswered() {
    if (!counted || cfg.mode !== 'pack') { return; }
    var n = cfg.items.filter(function (it) { return value(it) !== null; }).length;
    counted.textContent = n + ' ' + ui.of + ' ' + cfg.items.length + ' ' + ui.answered;
  }
  form.addEventListener('input', countAnswered);
  form.addEventListener('change', countAnswered);
  countAnswered();

  // checklists of the ids items: filter, only ticked, count
  function refreshChecklist(box) {
    var needle = box.querySelector('.ckf').value.trim().toLowerCase();
    var only = box.querySelector('.cko').checked;
    var shown = 0;
    all('.ckopt', box).forEach(function (o) {
      var on = o.querySelector('input').checked;
      var hit = (!needle || o.textContent.toLowerCase().indexOf(needle) >= 0) && (!only || on);
      o.classList.toggle('hide', !hit);
      if (hit) { shown += 1; }
    });
    all('.ckg', box).forEach(function (g) {
      g.classList.toggle('hide', !g.querySelector('.ckopt:not(.hide)'));
    });
    box.querySelector('.ckempty').classList.toggle('hide', shown > 0);
    var n = all('.ckopt input', box).filter(function (e) { return e.checked; }).length;
    box.querySelector('.ckn').textContent = ui.checked + ': ' + n + ' ' + ui.of + ' ' + box.getAttribute('data-total');
  }
  all('.ck').forEach(function (box) {
    refreshChecklist(box);
    box.addEventListener('input', function () { refreshChecklist(box); });
    box.addEventListener('change', function () { refreshChecklist(box); });
  });

  // replies (mode diff)
  function repliesYaml() {
    var L = ['record: "task_replies"', 'schema_version: "0.1"', 'diff: ' + q(cfg.diff),
      'member: ' + q(field('member')), 'date: ' + q(field('date'))];
    var out = [];
    var bad = [];
    cfg.points.forEach(function (p) {
      var c = checked('rc:' + p.id);
      if (!c.length) { return; }
      var f = ['choice: ' + q(c[0])];
      if (c[0] === 'accept') {
        var who = field('ra:' + p.id);
        if (!who || who === field('member')) { bad.push(p.name || p.id); return; }
        f.push('accept_member: ' + q(who));
      }
      var note = field('rn:' + p.id).trim();
      if (note) { f.push('note: ' + q(note)); }
      out.push('  ' + q(p.id) + ': {' + f.join(', ') + '}');
    });
    L.push(out.length ? 'replies:' : 'replies: {}');
    return { text: L.concat(out).join('\n') + '\n', bad: bad };
  }

  var go = document.getElementById('export');
  go.addEventListener('click', function () {
    var member = field('member');
    if (!member) { say(ui.missing_member, 'bad'); return; }
    if (cfg.mode === 'pack') {
      var lack = cfg.items.filter(function (it) { return it.required && value(it) === null; })
        .map(function (it) { return it.no; });
      var name = 'answers_' + member + '.yaml';
      download(name, answersYaml());
      say((lack.length ? ui.missing_required + lack.join(', ') + '. ' : '') + ui.exported + name, lack.length ? 'bad' : 'good');
    } else {
      var r = repliesYaml();
      if (r.bad.length) { say(ui.bad_accept + r.bad.join(', '), 'bad'); return; }
      var open = cfg.points.filter(function (p) { return p.open && !checked('rc:' + p.id).length; })
        .map(function (p) { return p.name || p.id; });
      var file = 'replies_' + member + '.yaml';
      download(file, r.text);
      say((open.length ? ui.unreplied + open.join(', ') + '. ' : '') + ui.exported + file, open.length ? 'bad' : 'good');
    }
  });

  // diff page: filter by class
  var flt = document.getElementById('flt');
  if (flt) {
    flt.addEventListener('change', function () {
      all('.pt').forEach(function (p) {
        var hit = flt.value === '' || p.getAttribute('data-class') === flt.value ||
          (flt.value === '(open)' && p.classList.contains('open'));
        p.classList.toggle('hide', !hit);
      });
    });
  }
  window.smdTask = { answersYaml: answersYaml, repliesYaml: repliesYaml };
}());
