/* ---------------------------------------------------------
   DPDP Navigator - Assessment Page JS
   Tech4Dev - dpdp.projecttech4dev.org
   Config loaded from: /assets/dpdp_tool/dpdp-config.json
   Requires: jsPDF (CDN)
--------------------------------------------------------- */
'use strict';

// Config and derived arrays - populated after fetch
let CFG = null;
let Q = [];
let SECTIONS = [];
let SEC_COUNTS = [];

// State
let org = {};
let answers = [];
let currentQ = 0;
let currentScreen = 's-intro';
let _autoSession = null;
let _docname = null;
let _pdfUrl = null;
let _pollTimer = null;

const FRAPPE_URL = '';

// ── CONFIG LOAD ─────────────────────────────────────────────────────
async function loadConfig() {
  try {
    const cached = sessionStorage.getItem('dpdp_cfg_v1');
    if (cached) { applyConfig(JSON.parse(cached)); return; }
    const r = await fetch('/assets/dpdp_tool/dpdp-config.json');
    if (!r.ok) throw new Error('Config fetch failed');
    const cfg = await r.json();
    sessionStorage.setItem('dpdp_cfg_v1', JSON.stringify(cfg));
    applyConfig(cfg);
  } catch(e) {
    console.warn('[dpdp] config load failed');
    document.querySelector('.btn-start').textContent = 'Error loading config — please refresh';
  }
}

function applyConfig(cfg) {
  CFG = cfg;
  SECTIONS = cfg.sections;
  Q = cfg.questions.map(q => ({
    s: q.section,
    t: q.text,
    w: q.why,
    o: q.options.map(o => [o.label, o.points])
  }));
  SEC_COUNTS = SECTIONS.map((_, i) => Q.filter(q => q.s === i).length);
  answers = new Array(Q.length).fill(null);
  renderSectorCheckboxes(cfg.sectors);
}

function renderSectorCheckboxes(sectors) {
  const el = document.getElementById('sector-checkboxes');
  if (!el) return;
  el.innerHTML = sectors.map(s =>
    `<label class="sector-cb"><input type="checkbox" value="${s}"> ${s}</label>`
  ).join('');
}

// ── SESSION STORAGE ─────────────────────────────────────────────────
const S_VER = 'dpdp_v1_';
const S_TTL = 7 * 24 * 60 * 60 * 1000;

function getSessionKey() {
  const e = document.getElementById('i-email')?.value?.trim().toLowerCase();
  return e ? S_VER + e : null;
}

function saveSession() {
  const key = getSessionKey();
  if (!key) return;
  const sectors = Array.from(document.querySelectorAll('#sector-checkboxes input:checked')).map(cb => cb.value);
  const completed      = currentScreen === 's-result';
  const summaryEl      = document.getElementById('summary-content');
  const roadmapTableEl = document.getElementById('roadmap-summary-table');
  const roadmapAccEl   = document.getElementById('roadmap-accordions');
  localStorage.setItem(key, JSON.stringify({
    answers, currentQ, completed,
    summaryHTML:      completed && summaryEl      ? summaryEl.innerHTML      : '',
    roadmapTableHTML: completed && roadmapTableEl ? roadmapTableEl.innerHTML : '',
    roadmapAccHTML:   completed && roadmapAccEl   ? roadmapAccEl.innerHTML   : '',
    pdfUrl: _pdfUrl || '',
    org: {
      org:    document.getElementById('i-org')?.value   || '',
      name:   document.getElementById('i-name')?.value  || '',
      email:  document.getElementById('i-email')?.value || '',
      sector: sectors,
      size:   document.getElementById('i-size')?.value  || '',
      bene:   document.getElementById('i-bene')?.value  || '',
    },
    savedAt: Date.now()
  }));
}

function loadSession(email) {
  try {
    const raw = localStorage.getItem(S_VER + email.trim().toLowerCase());
    if (!raw) return null;
    const data = JSON.parse(raw);
    if (Date.now() - data.savedAt > S_TTL) { localStorage.removeItem(S_VER + email.trim().toLowerCase()); return null; }
    return data;
  } catch { return null; }
}

function clearSession() {
  const key = getSessionKey();
  if (key) localStorage.removeItem(key);
}

function findLatestSession() {
  let best = null;
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (!key.startsWith(S_VER)) continue;
    try {
      const data = JSON.parse(localStorage.getItem(key));
      if (!data || Date.now() - data.savedAt > S_TTL) { localStorage.removeItem(key); continue; }
      if (!data.answers.some(a => a !== null)) continue;
      if (!best || data.savedAt > best.data.savedAt) best = { key, data };
    } catch {}
  }
  return best;
}

function restoreSession(saved) {
  if (saved.org.org)   document.getElementById('i-org').value   = saved.org.org;
  if (saved.org.name)  document.getElementById('i-name').value  = saved.org.name;
  if (saved.org.email) document.getElementById('i-email').value = saved.org.email;
  if (saved.org.size)  document.getElementById('i-size').value  = saved.org.size;
  if (saved.org.bene)  document.getElementById('i-bene').value  = saved.org.bene;
  document.querySelectorAll('#sector-checkboxes input[type=checkbox]').forEach(cb => {
    cb.checked = (saved.org.sector || []).includes(cb.value);
  });
  answers = saved.answers;
  currentQ = saved.currentQ;
  org = saved.org;
  document.getElementById('resume-prompt')?.remove();
  const warn = document.getElementById('session-warn');
  if (warn) warn.textContent = 'Session resumed — progress is auto-saved';
  showScreen('s-assess');
  renderQ(currentQ);
}

function resumeFromAuto() {
  const found = findLatestSession();
  if (found) restoreSession(found.data);
}

function discardAuto(key) {
  localStorage.removeItem(key);
  document.getElementById('resume-prompt')?.remove();
  document.querySelector('.org-form').style.display = '';
}

function viewReport() {
  if (!_autoSession) return;
  const saved = _autoSession.data;
  answers = saved.answers;
  org = saved.org;
  _pdfUrl = saved.pdfUrl || null;
  if (saved.org.email) document.getElementById('i-email').value = saved.org.email;
  const { secScores, total } = calcScores();
  showScreen('s-result');
  setResultHero(total);
  renderSGrid(secScores);
  renderQBreakdown();
  renderGlossary();
  renderReferences();
  if (saved.summaryHTML) document.getElementById('summary-content').innerHTML = saved.summaryHTML;
  if (saved.roadmapTableHTML || saved.roadmapAccHTML) {
    document.getElementById('roadmap-pending')?.remove();
    if (saved.roadmapTableHTML) document.getElementById('roadmap-summary-table').innerHTML = saved.roadmapTableHTML;
    if (saved.roadmapAccHTML)   document.getElementById('roadmap-accordions').innerHTML   = saved.roadmapAccHTML;
  }
  if (_pdfUrl) {
    const btn = document.getElementById('btn-pdf');
    btn.disabled = false;
  }
}

// ── NAV ─────────────────────────────────────────────────────────────
function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  currentScreen = id;
  window.scrollTo(0, 0);
}

function switchTab(btn) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById(btn.dataset.tab).classList.add('active');
}

window.addEventListener('beforeunload', e => {
  if (currentScreen === 's-assess' && !getSessionKey()) {
    e.preventDefault(); e.returnValue = '';
  }
});

// ── AUTO SESSION DETECT ─────────────────────────────────────────────
(function checkOnLoad() {
  const found = findLatestSession();
  if (!found) return;
  _autoSession = found;
  const saved = found.data;
  const name = saved.org.name || saved.org.org || '';
  const banner = document.createElement('div');
  banner.id = 'resume-prompt';
  banner.className = 'session-warn';
  banner.style.cssText = 'margin-bottom:1.5rem;justify-content:space-between;flex-wrap:wrap;gap:.5rem';
  if (saved.completed) {
    banner.innerHTML = `
      <span>Welcome back${name ? ' <strong>' + name + '</strong> —' : ' —'} your assessment is complete. View your report or start fresh.</span>
      <span style="display:flex;gap:.5rem;flex-shrink:0">
        <button onclick="viewReport()" class="btn-next" style="padding:5px 12px;font-size:.80rem">View Report</button>
        <button onclick="discardAuto('${found.key}')" class="btn-prev" style="padding:5px 12px;font-size:.80rem">Start fresh</button>
      </span>`;
  } else {
    const answered = saved.answers.filter(a => a !== null).length;
    const pct = Math.round(answered / saved.answers.length * 100);
    banner.innerHTML = `
      <span>Welcome back${name ? ' <strong>' + name + '</strong> —' : ' —'} <strong>${pct}% complete</strong> (${answered} of ${saved.answers.length} answered)</span>
      <span style="display:flex;gap:.5rem;flex-shrink:0">
        <button onclick="resumeFromAuto()" class="btn-next" style="padding:5px 12px;font-size:.80rem">Resume</button>
        <button onclick="discardAuto('${found.key}')" class="btn-prev" style="padding:5px 12px;font-size:.80rem">Start fresh</button>
      </span>`;
  }
  const wrap = document.querySelector('.intro-wrap');
  if (wrap) wrap.prepend(banner);
  document.querySelector('.org-form').style.display = 'none';
})();

// ── START ────────────────────────────────────────────────────────────
function startAssessment() {
  if (!CFG) { alert('Configuration still loading — please wait a moment.'); return; }
  const o  = document.getElementById('i-org').value.trim();
  const n  = document.getElementById('i-name').value.trim();
  const e  = document.getElementById('i-email').value.trim();
  const sc = Array.from(document.querySelectorAll('#sector-checkboxes input:checked')).map(cb => cb.value);
  const sz = document.getElementById('i-size').value;
  if (!o || !n || !e || sc.length === 0 || !sz) {
    alert('Please fill in all required fields and select at least one sector.');
    return;
  }
  org = { org: o, name: n, email: e, sector: sc, size: sz, bene: document.getElementById('i-bene').value.trim() };
  showScreen('s-assess');
  currentQ = 0;
  renderQ(0);
  saveSession();
}

// ── RENDER QUESTION ──────────────────────────────────────────────────
function renderQ(idx) {
  const q = Q[idx]; const tot = Q.length;
  const pct = Math.round(((idx + 1) / tot) * 100);
  const secIdx = q.s; const sec = SECTIONS[secIdx];
  const priorQ = SEC_COUNTS.slice(0, secIdx).reduce((a, b) => a + b, 0);
  const qInSec = idx - priorQ + 1; const totInSec = SEC_COUNTS[secIdx];

  document.getElementById('prog-fill').style.width = pct + '%';
  document.getElementById('prog-cnt').textContent = `Question ${idx + 1} of ${tot}`;
  document.getElementById('prog-sec').textContent = `${sec.label} · ${qInSec} of ${totInSec}`;

  const sel = answers[idx];
  document.getElementById('q-area').innerHTML = `
    <div class="sec-badge">Section ${secIdx + 1} — ${sec.label}</div>
    <div class="q-card">
      <div class="q-num">Q${idx + 1}</div>
      <div class="q-text">${q.t}</div>
      ${q.w ? `<div class="q-why">${q.w}</div>` : ''}
      <div class="opts">${q.o.map((opt, oi) => `
        <div class="opt${sel === oi ? ' sel' : ''}" onclick="selectOpt(${idx},${oi})">
          <div class="opt-radio"></div>
          <div class="opt-label">${opt[0]}</div>
        </div>`).join('')}
      </div>
    </div>`;

  document.getElementById('btn-prev').style.visibility = idx === 0 ? 'hidden' : 'visible';
  document.getElementById('btn-next').textContent = idx === tot - 1 ? 'Submit' : 'Next';
  document.getElementById('btn-next').disabled = (sel === null);
}

function selectOpt(qIdx, oi) { answers[qIdx] = oi; renderQ(qIdx); saveSession(); }
function nextQ() {
  if (answers[currentQ] === null) return;
  if (currentQ === Q.length - 1) { submitAssessment(); }
  else { currentQ++; renderQ(currentQ); saveSession(); }
}
function prevQ() {
  if (currentQ > 0) { currentQ--; renderQ(currentQ); saveSession(); }
}

// ── SCORING ──────────────────────────────────────────────────────────
function calcScores() {
  const secScores = SECTIONS.map((_, si) => {
    const qs = Q.filter(q => q.s === si);
    const scored = qs.filter((_, qi) => answers[Q.indexOf(qs[qi])] !== null);
    if (!scored.length) return null;
    return qs.reduce((sum, q) => {
      const gi = Q.indexOf(q); const a = answers[gi];
      if (a === null) return sum;
      return sum + Q[gi].o[a][1];
    }, 0);
  });
  const total = secScores.filter(s => s !== null).reduce((a, b) => a + b, 0);
  const maxTotal = Q.reduce((s, q) => s + Math.max(...q.o.map(o => o[1])), 0);
  return { secScores, total, maxTotal };
}

function getBand(total) {
  const bands = CFG?.scoring?.bands || [
    {min:46,label:'Strong Readiness',emoji:'🟢',color:'green'},
    {min:36,label:'Moderate Readiness',emoji:'🟠',color:'amber'},
    {min:21,label:'Basic Readiness — Needs Work',emoji:'🟡',color:'orange'},
    {min:0, label:'High Risk — Not Ready',emoji:'🔴',color:'red'}
  ];
  return bands.find(b => total >= b.min) || bands[bands.length - 1];
}

function getSectionBand(pct) {
  const bands = CFG?.scoring?.section_bands || [
    {min_pct: 70, label: 'Strong',       color: 'green'},
    {min_pct: 40, label: 'Developing',   color: 'amber'},
    {min_pct: 0,  label: 'Priority gap', color: 'red'}
  ];
  return bands.find(b => pct >= b.min_pct) || bands[bands.length - 1];
}

// ── SUBMIT ───────────────────────────────────────────────────────────
async function submitAssessment() {
  const { secScores, total } = calcScores();
  showScreen('s-result');

  // Render static content immediately
  setResultHero(total);
  renderSGrid(secScores);
  renderQBreakdown();
  renderGlossary();
  renderReferences();

  // Show email in roadmap tab
  const emailEl = document.getElementById('roadmap-email');
  if (emailEl) emailEl.textContent = org.email;

  // Show status bar
  updateStatusBar('processing');

  // Store in Frappe, then start both AI calls in parallel
  _docname = await storeInFrappe(secScores, total);

  await Promise.allSettled([
    fetchSummary(secScores, total),
    fetchRoadmap(secScores, total)
  ]);

  // Start polling for PDF
  if (_docname) pollForPDF();
}

function setResultHero(total) {
  const band = getBand(total);
  document.getElementById('rh-org').textContent =
    `${org.org} · ${Array.isArray(org.sector) ? org.sector.join(', ') : org.sector} · ${org.size}`;
  animateScore('rh-score', total);
  const bandEl = document.getElementById('rh-band');
  bandEl.textContent = `${band.emoji} ${band.label}`;
  bandEl.className = 'rh-band band-' + (band.color || 'red');
}

function animateScore(id, target) {
  const el = document.getElementById(id); let cur = 0;
  const step = Math.ceil(target / 40);
  const t = setInterval(() => {
    cur = Math.min(cur + step, target);
    el.textContent = cur;
    if (cur >= target) clearInterval(t);
  }, 30);
}

// ── RENDER RESULTS ───────────────────────────────────────────────────
function renderSGrid(secScores) {
  const sgEl = document.getElementById('sgrid');
  if (!sgEl) return;
  sgEl.innerHTML = SECTIONS.map((sec, i) => {
    const raw = secScores[i] !== null ? secScores[i] : 0;
    const maxSec = SEC_COUNTS[i] * 2;
    const pct = Math.round((raw / maxSec) * 100);
    const sb   = getSectionBand(pct);
    const band = sb.color === 'green' ? 'high' : sb.color === 'amber' ? 'mid' : 'low';
    const lbl  = sb.label;
    return `<div class="scard ${band}" style="animation-delay:${i * .07}s">
      <div class="sc-name">Section ${i + 1} · ${sec.label}</div>
      <div class="sc-pct ${band}">${raw}/${maxSec}</div>
      <div class="sc-bar"><div class="sc-bar-fill fill-${band}" style="width:${pct}%"></div></div>
      <div class="sc-lbl">${lbl} · ${pct}%</div>
    </div>`;
  }).join('');
}


function renderQBreakdown() {
  const qbEl = document.getElementById('qb-secs');
  if (!qbEl) return;
  qbEl.innerHTML = SECTIONS.map((sec, si) => {
    const qs = Q.filter(q => q.s === si);
    return `<div>
      <div class="qb-sec-title">Section ${si + 1} — ${sec.label}</div>
      <div class="qb-rows">${qs.map(q => {
        const gi = Q.indexOf(q); const a = answers[gi];
        if (a === null) return '';
        const pts = Q[gi].o[a][1];
        const cls = pts === 2 ? 'ans-yes' : pts === 1 ? 'ans-part' : 'ans-no';
        const lbl = pts === 2 ? 'Yes' : pts === 1 ? 'Partially' : 'No';
        const chipCls = pts === 2 ? 'chip-yes' : pts === 1 ? 'chip-part' : 'chip-no';
        const why = (q.w || '').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
        return `<div class="qb-row"${why ? ` data-why="${why}"` : ''}>
          <div class="q-num-chip ${chipCls}">Q${gi + 1}</div>
          <div class="qb-q">${q.t}</div>
          <div class="qb-ans ${cls}">${lbl}</div>
        </div>`;
      }).join('')}</div>
    </div>`;
  }).join('');
}

function renderGlossary() {
  const el = document.getElementById('glossary-box');
  if (!el || !CFG?.glossary) return;
  document.getElementById('glossary-box').innerHTML = `
    <h3>Key Terms</h3>
    <div class="glossary-list">
      ${CFG.glossary.map(g => `
        <div class="glossary-item">
          <div class="glossary-term">${g.term} <span class="glossary-ref">· ${g.reference}</span></div>
          <div class="glossary-def">${g.definition}</div>
        </div>`).join('')}
    </div>`;
}

function renderReferences() {
  const el = document.getElementById('refs-box');
  if (!el || !CFG?.references) return;
  document.getElementById('refs-box').innerHTML = `
    <h3>Further Reading</h3>
    <div class="refs-list">
      ${CFG.references.map(r => `
        <a href="${r.url}" target="_blank" rel="noopener" class="ref-link">
          <span class="ref-title">${r.title}</span>
          ${r.note ? `<span class="ref-note">${r.note}</span>` : ''}
        </a>`).join('')}
    </div>`;
}

// ── STATUS BAR ───────────────────────────────────────────────────────
function updateStatusBar(state) {
  const bar = document.getElementById('reco-status');
  if (!bar) return;
  bar.style.display = 'block';

  // Step definitions per state
  // States: 'processing' | 'summary_ready' | 'roadmap_ready' | 'complete'
  const stepState = (key) => {
    const order = ['scores','summary','roadmap','pdf','email'];
    const doneAt = {
      processing:    ['scores'],
      summary_ready: ['scores','summary'],
      roadmap_ready: ['scores','summary','roadmap'],
      complete:      ['scores','summary','roadmap','pdf','email'],
    }[state] || ['scores'];
    const activeAt = {
      processing:    'summary',
      summary_ready: 'roadmap',
      roadmap_ready: 'pdf',
      complete:      null,
    }[state];
    if (doneAt.includes(key))  return 'done';
    if (activeAt === key)       return 'active';
    // pdf and email both spin during roadmap_ready
    if (state === 'roadmap_ready' && key === 'email') return 'active';
    return 'pending';
  };

  const steps = [
    {key:'scores',  label:'Scores'},
    {key:'summary', label:'Summary'},
    {key:'roadmap', label:'Roadmap'},
    {key:'pdf',     label:'PDF'},
    {key:'email',   label:'Email'},
  ];

  const stepHTML = steps.map((s, i) => {
    const st = stepState(s.key);
    const icon = st === 'done'
      ? '<span class="ss-check">&#10003;</span>'
      : st === 'active'
        ? '<span class="ss-spin"></span>'
        : '<span class="ss-dot"></span>';
    return `<div class="ss-step ss-${st}">${icon}${s.label}</div>`
      + (i < steps.length - 1 ? '<div class="ss-connector"></div>' : '');
  }).join('');

  // Complete: tracker only, no second bar
  if (state === 'complete') {
    bar.innerHTML = `<div class="ss-steps ss-steps-complete">${stepHTML}</div>`;
    return;
  }

  const cfg = {
    processing:    {cls:'ss-bar-processing', icon:'<span class="ss-spin-lg"></span>', text:'Generating your executive summary\u2026'},
    summary_ready: {cls:'ss-bar-info',       icon:'<span class="ss-dot-info"></span>',    text:'Executive summary ready. Action roadmap is generating in the background.', btn:{label:'View summary \u2192',tab:'tab-summary'}},
    roadmap_ready: {cls:'ss-bar-success',    icon:'<span class="ss-dot-success"></span>', text:'Roadmap ready. PDF is being prepared and will be emailed to you.',          btn:{label:'View roadmap \u2192',tab:'tab-roadmap'}},
  }[state];

  bar.innerHTML = `
    <div class="ss-steps">${stepHTML}</div>
    <div class="ss-bar ${cfg.cls}">
      ${cfg.icon}
      <div class="ss-text">${cfg.text}</div>
      ${cfg.btn ? `<button class="ss-btn" onclick="switchTabByName('${cfg.btn.tab}')">${cfg.btn.label}</button>` : ''}
    </div>`;
}

function switchTabByName(tabId) {
  const btn = document.querySelector('.tab[data-tab="' + tabId + '"]');
  if (btn) switchTab(btn);
}

// ── FRAPPE STORAGE ───────────────────────────────────────────────────
function buildAnswerSummary() {
  return JSON.stringify(answers.map((a, i) => ({
    q: i + 1,
    section: SECTIONS[Q[i]?.s]?.label || '',
    text: Q[i]?.t || '',
    why:  Q[i]?.w || '',
    answer_idx: a,
    answer_label: a !== null ? (Q[i]?.o[a]?.[0] || '') : '',
    points: a !== null ? (Q[i]?.o[a]?.[1] ?? 0) : 0
  })));
}

async function storeInFrappe(secScores, total) {
  // Field names match existing DPDP Assessment DocType exactly.
  console.log('[dpdp] storing assessment');
  try {
    const body = {
      org_name:         org.org,
      org_email:        org.email,
      contact_name:     org.name,
      sector:           JSON.stringify(Array.isArray(org.sector) ? org.sector : [org.sector]),
      org_size:         org.size,
      beneficiaries:    org.bene || '',
      total_score:      total,
      score_consent:    secScores[0] || 0,
      score_storage:    secScores[1] || 0,
      score_usage:      secScores[2] || 0,
      score_rights:     secScores[3] || 0,
      score_governance: secScores[4] || 0,
      answers_json:     buildAnswerSummary(),
    };
    const res = await fetch(`${FRAPPE_URL}/api/method/dpdp_tool.api.store_assessment`, {
      method: 'POST',
      headers: { 'X-Frappe-CSRF-Token': 'fetch' },
      body: new URLSearchParams(body)
    });
    if (!res.ok) {
      console.warn('[dpdp] store failed:', res.status);
      return null;
    }
    const j = await res.json();
    if (j.message?.status === 'error') {
      console.warn('[dpdp] store API error');
      return null;
    }
    console.log('[dpdp] store complete');
    return j.message?.docname || null;
  } catch(e) {
    console.warn('[dpdp] store exception');
    return null;
  }
}

// ── CALL 1: EXECUTIVE SUMMARY ────────────────────────────────────────
async function fetchSummary(secScores, total) {
  const steps = [
    'Mapping scores to sector risk profile…',
    'Identifying beneficiary-specific risks…',
    'Assessing regulatory exposure…',
    'Preparing executive summary…'
  ];
  let si = 0;
  const stepEl = document.getElementById('summary-step');
  const t = setInterval(() => { si = (si + 1) % steps.length; if (stepEl) stepEl.textContent = steps[si]; }, 3000);

  try {
    if (!_docname) throw new Error('no docname');
    console.log('[dpdp] polling summary');
    // Poll for summary from Frappe (background job started by storeInFrappe)
    await pollForField('summary-content', 'executive_summary', _docname, t, renderSummary);
    console.log('[dpdp] summary ready');
  } catch(e) {
    clearInterval(t);
    console.warn('[dpdp] summary failed');
    document.getElementById('summary-content').innerHTML =
      `<p style="color:var(--muted);padding:1rem 0">Summary generation failed — please retake the assessment.</p>`;
  }
}

// ── CALL 2: ACTION ROADMAP ───────────────────────────────────────────
async function fetchRoadmap(secScores, total) {
  try {
    if (!_docname) throw new Error('no docname');
    console.log('[dpdp] polling roadmap');
    await pollForField('roadmap-accordions', 'action_roadmap', _docname, null, renderRoadmap);
    console.log('[dpdp] roadmap ready');
    saveSession();
  } catch(e) {
    console.warn('[dpdp] roadmap failed');
    document.getElementById('roadmap-pending')?.remove();
    document.getElementById('roadmap-accordions').innerHTML =
      `<p style="color:var(--muted);padding:1rem 0">Roadmap generation failed. Check your email — we may have emailed it already.</p>`;
  }
}

// Generic poll for a Frappe field
async function pollForField(contentId, field, docname, intervalTimer, renderFn) {
  const MAX = 60; // 60 x 5s = 5 min
  for (let i = 0; i < MAX; i++) {
    await new Promise(r => setTimeout(r, 5000));
    try {
      const res = await fetch(
        `${FRAPPE_URL}/api/method/dpdp_tool.api.poll_status?docname=${encodeURIComponent(docname)}`,
        { headers: { 'X-Frappe-CSRF-Token': 'fetch' } }
      );
      const j = await res.json();
      const st = j.message;
      if (st?.[field]) {
        if (intervalTimer) clearInterval(intervalTimer);
        renderFn(st[field]);
        return;
      }
      if (st?.status === 'failed') throw new Error(st.failed_reason || 'processing failed');
    } catch(e) { console.warn('[dpdp] poll retry'); }
  }
  throw new Error('Poll timeout');
}

function renderSummary(md) {
  document.getElementById('summary-content').innerHTML = markdownToHTML(md);
  updateStatusBar('summary_ready');
}



// Minimal markdown renderer for bullet/heading/table output from Claude
function markdownToHTML(md) {
  if (!md) return '';
  let html = md
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    // Links [text](url) — before italic so surrounding * still works
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener" class="md-link">$1</a>')
    // Tables (handle separator row and data rows)
    .replace(/\|(.+)\|\n\|[-| :]+\|\n((?:\|.+\|\n?)*)/g, (_, header, rows) => {
      const th = header.split('|').filter(c => c.trim()).map(c => `<th>${c.trim()}</th>`).join('');
      const trs = rows.trim().split('\n').filter(r => r.includes('|')).map(r =>
        '<tr>' + r.split('|').slice(1, -1).map(c => `<td>${c.trim()}</td>`).join('') + '</tr>'
      ).join('');
      return `<div class="md-table-wrap"><table class="md-table"><thead><tr>${th}</tr></thead><tbody>${trs}</tbody></table></div>`;
    })
    // Footnotes (* text at line start, not **bold**)
    .replace(/^\* ([^*\n].+)$/gm, '<p class="md-footnote">* $1</p>')
    // Headings
    .replace(/^### (.+)$/gm, '<h4 class="md-h3">$1</h4>')
    .replace(/^## (.+)$/gm,  '<h3 class="md-h2">$1</h3>')
    .replace(/^# (.+)$/gm,   '<h2 class="md-h1">$1</h2>')
    // Bold (before italic)
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    // Italic
    .replace(/\*([^*\n]+)\*/g, '<em>$1</em>')
    // Bullets — only - prefix (not * which is footnote/italic)
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>[\s\S]*?<\/li>\n?)+/g, '<ul>$&</ul>')
    // Paragraphs
    .replace(/\n\n+/g, '</p><p>')
    .trim();
  return `<div class="md-body"><p>${html}</p></div>`;
}

// ── PDF ──────────────────────────────────────────────────────────────
async function pollForPDF() {
  const MAX = 72; // 72 x 5s = 6 min
  for (let i = 0; i < MAX; i++) {
    await new Promise(r => setTimeout(r, 5000));
    try {
      const res = await fetch(
        `${FRAPPE_URL}/api/method/dpdp_tool.api.poll_status?docname=${encodeURIComponent(_docname)}`,
        { headers: { 'X-Frappe-CSRF-Token': 'fetch' } }
      );
      const j = await res.json();
      if (j.message?.pdf_file) {
        _pdfUrl = FRAPPE_URL + j.message.pdf_file;
        const btn = document.getElementById('btn-pdf');
        btn.disabled = false;
        updateStatusBar('complete');
        saveSession();
        return;
      }
    } catch(e) { console.warn('[dpdp] pdf poll retry'); }
  }
  // Fallback to client-side jsPDF
  const btn = document.getElementById('btn-pdf');
  btn.disabled = false;
}

function downloadPDF() {
  if (_pdfUrl) {
    window.open(_pdfUrl, '_blank');
  } else {
    generatePDFFallback();
  }
}

// Client-side jsPDF fallback
function generatePDFFallback() {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ unit: 'mm', format: 'a4' });
  const { secScores, total } = calcScores();
  const band = getBand(total);
  const W = 210, M = 18, CW = W - M * 2;
  let y = 0;
  const chk = (n = 15) => { if (y + n > 270) { doc.addPage(); y = 20; } };
  const hdr = (pg) => {
    if (pg > 1) {
      doc.setFillColor(26,43,74); doc.rect(0,0,W,10,'F');
      doc.setTextColor(255,255,255); doc.setFontSize(7);
      doc.text('DPDP READINESS REPORT · ' + org.org.toUpperCase(), M, 7);
    }
  };

  // Cover
  doc.setFillColor(26,43,74); doc.rect(0,0,W,297,'F');
  doc.setFillColor(29,111,184); doc.rect(0,0,5,297,'F');
  doc.setTextColor(126,184,240); doc.setFontSize(8); doc.setFont('helvetica','normal');
  doc.text('TECH4DEV · DPDP READINESS NAVIGATOR', M, 40);
  doc.setTextColor(255,255,255); doc.setFontSize(24); doc.setFont('helvetica','bold');
  doc.text('DPDP Compliance', M, 78); doc.text('Readiness Report', M, 91);
  doc.setTextColor(126,184,240); doc.setFontSize(46);
  doc.text(`${total}/50`, M, 140);
  doc.setTextColor(160,185,210); doc.setFontSize(10); doc.setFont('helvetica','normal');
  doc.text('Overall readiness score', M, 150);
  doc.setTextColor(255,255,255); doc.setFontSize(14);
  doc.text(org.org, M, 180);
  doc.setFontSize(10); doc.setTextColor(140,165,200);
  const sectorStr = Array.isArray(org.sector) ? org.sector.join(', ') : org.sector;
  doc.text(`${sectorStr} · ${org.size}`, M, 188);
  doc.text('Assessed: ' + new Date().toLocaleDateString('en-IN',{day:'numeric',month:'long',year:'numeric'}), M, 196);
  doc.setTextColor(126,184,240); doc.setFontSize(9);
  doc.text(band.label, M, 210);

  // Page 2: Section scores
  doc.addPage(); hdr(2); y = 22;
  doc.setTextColor(26,43,74); doc.setFontSize(15); doc.setFont('helvetica','bold');
  doc.text('Section Score Summary', M, y); y += 12;
  SECTIONS.forEach((sec, i) => {
    chk(22);
    const raw = secScores[i] || 0; const max = SEC_COUNTS[i] * 2;
    const pct = Math.round((raw / max) * 100);
    /* jsPDF draws to a non-DOM canvas so CSS variables are unavailable here.
       These RGB values must match --score-high/mid/low in dpdp.css. */
    const col = (() => { const sb = getSectionBand(pct); return sb.color === 'green' ? [29,111,184] : sb.color === 'amber' ? [146,64,14] : [185,28,28]; })();
    doc.setFontSize(9); doc.setFont('helvetica','bold'); doc.setTextColor(26,43,74);
    doc.text(`Section ${i + 1}: ${sec.label}`, M, y);
    doc.setFontSize(8); doc.setFont('helvetica','normal'); doc.setTextColor(74,85,104);
    doc.text(`${raw} of ${max} points`, M + CW - 28, y); y += 5;
    doc.setFillColor(220,226,232); doc.roundedRect(M, y, CW-35, 5, 1, 1, 'F');
    doc.setFillColor(...col); doc.roundedRect(M, y, (CW-35) * pct / 100, 5, 1, 1, 'F');
    y += 14;
  });

  // Page 3: Q&A with why text
  doc.addPage(); hdr(3); y = 22;
  doc.setTextColor(26,43,74); doc.setFontSize(15); doc.setFont('helvetica','bold');
  doc.text('Question-by-Question Breakdown', M, y); y += 12;
  SECTIONS.forEach((sec, si) => {
    chk(20);
    doc.setFontSize(9); doc.setFont('helvetica','bold'); doc.setTextColor(29,111,184);
    doc.text(`SECTION ${si + 1} — ${sec.label.toUpperCase()}`, M, y); y += 7;
    Q.filter(q => q.s === si).forEach(q => {
      chk(20);
      const gi = Q.indexOf(q); const a = answers[gi];
      const pts = Q[gi].o[a]?.[1] || 0;
      const lbl = pts === 2 ? 'Yes' : pts === 1 ? 'Partially' : 'No';
      const col = pts === 2 ? [22,163,74] : pts === 1 ? [217,119,6] : [185,28,28];
      // Q number chip
      doc.setFillColor(...col); doc.roundedRect(M, y-3, 8, 5, 1, 1, 'F');
      doc.setTextColor(255,255,255); doc.setFontSize(6.5); doc.setFont('helvetica','bold');
      doc.text(`Q${gi+1}`, M+1.2, y);
      // Question text
      doc.setFontSize(8); doc.setFont('helvetica','normal'); doc.setTextColor(26,43,74);
      const qLines = doc.splitTextToSize(q.t, CW - 25);
      qLines.slice(0, 2).forEach((l, li) => { doc.text(l, M + 10, y + li * 4.5); });
      // Answer label
      doc.setFont('helvetica','bold'); doc.setTextColor(...col);
      doc.text(lbl, M + CW - 16, y);
      y += 6.5;
      // Why text
      if (q.w) {
        chk(10);
        doc.setFont('helvetica','italic'); doc.setFontSize(7); doc.setTextColor(100,116,139);
        doc.splitTextToSize(q.w, CW - 12).slice(0, 2).forEach((l, li) => {
          doc.text(l, M + 10, y + li * 3.8);
        });
        y += 8;
      }
      y += 2;
    });
    y += 4;
  });

  // Page 4+: Executive Summary
  const summaryText = document.getElementById('summary-content')?.innerText || '';
  if (summaryText && summaryText.length > 50) {
    doc.addPage(); hdr(doc.getNumberOfPages()); y = 22;
    doc.setTextColor(26,43,74); doc.setFontSize(15); doc.setFont('helvetica','bold');
    doc.text('Executive Summary', M, y); y += 12;
    summaryText.split('\n').filter(l => l.trim()).forEach(line => {
      chk(10);
      if (line.startsWith('  ') || line.startsWith('•')) {
        doc.setFontSize(8); doc.setFont('helvetica','normal'); doc.setTextColor(26,43,74);
        doc.splitTextToSize('• ' + line.trim().replace(/^[•-]\s*/, ''), CW).forEach(wl => {
          chk(6); doc.text(wl, M + 4, y); y += 5;
        }); y += 1;
      } else {
        doc.setFontSize(9.5); doc.setFont('helvetica','bold'); doc.setTextColor(29,111,184);
        doc.text(line.trim(), M, y); y += 7;
      }
    });
  }

  // Page: Action Roadmap
  const roadmapAccEl = document.getElementById('roadmap-accordions');
  const roadmapText = roadmapAccEl ? roadmapAccEl.innerText : '';
  if (roadmapText && roadmapText.length > 50) {
    doc.addPage(); hdr(doc.getNumberOfPages()); y = 22;
    doc.setTextColor(26,43,74); doc.setFontSize(15); doc.setFont('helvetica','bold');
    doc.text('30 / 90 / 365-Day Action Roadmap', M, y); y += 12;
    roadmapText.split('\n').filter(l => l.trim()).forEach(line => {
      chk(10);
      if (line.match(/^(30|90|365)-Day/i) || line.match(/^##/)) {
        y += 3; doc.setFontSize(10); doc.setFont('helvetica','bold'); doc.setTextColor(29,111,184);
        doc.text(line.replace(/^#+\s*/, '').trim(), M, y); y += 7;
      } else if (line.startsWith('|')) {
        // Skip markdown table markers
      } else {
        doc.setFontSize(8); doc.setFont('helvetica','normal'); doc.setTextColor(26,43,74);
        doc.splitTextToSize(line.trim(), CW).forEach(wl => { chk(6); doc.text(wl, M, y); y += 5; }); y += 1;
      }
    });
  }

  // Appendix A: Glossary
  if (CFG?.glossary) {
    doc.addPage(); hdr(doc.getNumberOfPages()); y = 22;
    doc.setTextColor(26,43,74); doc.setFontSize(15); doc.setFont('helvetica','bold');
    doc.text('Appendix A — Key Terms', M, y); y += 12;
    CFG.glossary.forEach(g => {
      chk(20);
      doc.setFontSize(9); doc.setFont('helvetica','bold'); doc.setTextColor(26,43,74);
      doc.text(g.term, M, y);
      doc.setFontSize(7.5); doc.setFont('helvetica','italic'); doc.setTextColor(100,116,139);
      doc.text(g.reference, M + CW - 30, y); y += 5;
      doc.setFont('helvetica','normal'); doc.setTextColor(74,85,104);
      doc.splitTextToSize(g.definition, CW).forEach(l => { chk(5); doc.text(l, M, y); y += 4.5; });
      y += 4;
    });
  }

  // Appendix B: References
  if (CFG?.references) {
    doc.addPage(); hdr(doc.getNumberOfPages()); y = 22;
    doc.setTextColor(26,43,74); doc.setFontSize(15); doc.setFont('helvetica','bold');
    doc.text('Appendix B — Further Reading', M, y); y += 12;
    CFG.references.forEach(r => {
      chk(16);
      doc.setFontSize(9); doc.setFont('helvetica','bold'); doc.setTextColor(29,111,184);
      doc.text(r.title, M, y); y += 5;
      doc.setFontSize(8); doc.setFont('helvetica','normal'); doc.setTextColor(74,85,104);
      doc.text(r.url, M, y); y += 4;
      if (r.note) { doc.setFontSize(7.5); doc.setTextColor(100,116,139); doc.text(r.note, M, y); y += 4; }
      y += 4;
    });
  }

  // Footer on all content pages
  const tot = doc.getNumberOfPages();
  for (let p = 2; p <= tot; p++) {
    doc.setPage(p);
    doc.setFillColor(232,236,245); doc.rect(0,285,W,12,'F');
    doc.setFontSize(7); doc.setFont('helvetica','normal'); doc.setTextColor(74,85,104);
    doc.text('Tech4Dev · DPDP Readiness Navigator · dpdp.projecttech4dev.org', M, 292);
    doc.text(`Page ${p} of ${tot}`, W - M - 15, 292);
  }
  doc.save(`DPDP_${org.org.replace(/\s+/g,'_')}_${new Date().toISOString().slice(0,10)}.pdf`);
}

// ── VIEW REPORT (from cached session) ───────────────────────────────
function viewReport() {
  if (!_autoSession) return;
  const saved = _autoSession.data;
  answers = saved.answers; org = saved.org; _pdfUrl = saved.pdfUrl || null;
  if (saved.org.email) document.getElementById('i-email').value = saved.org.email;
  const { secScores, total } = calcScores();
  showScreen('s-result');
  setResultHero(total);
  renderSGrid(secScores);
  renderQBreakdown();
  renderGlossary();
  renderReferences();
  const emailEl = document.getElementById('roadmap-email');
  if (emailEl) emailEl.textContent = org.email;
  if (saved.summaryHTML) document.getElementById('summary-content').innerHTML = saved.summaryHTML;
  if (saved.roadmapTableHTML || saved.roadmapAccHTML) {
    document.getElementById('roadmap-pending')?.remove();
    if (saved.roadmapTableHTML) document.getElementById('roadmap-summary-table').innerHTML = saved.roadmapTableHTML;
    if (saved.roadmapAccHTML)   document.getElementById('roadmap-accordions').innerHTML   = saved.roadmapAccHTML;
  }
  if (_pdfUrl) document.getElementById('btn-pdf').disabled = false;
}

// ── RESTART ──────────────────────────────────────────────────────────
function restartAssessment() {
  clearSession();
  answers = new Array(Q.length).fill(null);
  currentQ = 0; _docname = null; _pdfUrl = null;
  document.getElementById('btn-pdf').disabled = true;
  showScreen('s-intro');
  document.querySelector('.org-form').style.display = '';
}

// ── ROADMAP RENDERING ──────────────────────────────────────────────

function parseRoadmapSections(md) {
  const out = {};
  const parts = md.split(/^## /m);
  for (const part of parts) {
    if (!part.trim()) continue;
    const nl   = part.indexOf('\n');
    const head = nl === -1 ? part : part.slice(0, nl);
    const body = nl === -1 ? '' : part.slice(nl + 1).trim();
    const h    = head.toLowerCase();
    if      (h.includes('30'))                                   out['30']    = body;
    else if (h.includes('90'))                                   out['90']    = body;
    else if (h.includes('365') || h.includes('year'))            out['365']   = body;
    else if (h.includes('summary') || h.includes('table'))       out['table'] = body;
  }
  return out;
}

function renderRoadmap(md) {
  document.getElementById('roadmap-pending')?.remove();
  updateStatusBar('roadmap_ready');
  const secs = parseRoadmapSections(md);
  // Summary table at top
  const tableEl = document.getElementById('roadmap-summary-table');
  if (tableEl && secs.table) {
    tableEl.innerHTML = `<div class="roadmap-table-hdr">Action Summary</div>${markdownToHTML(secs.table)}`;
  }
  // Accordions for each time period
  const periods = [
    {key:'30',  label:'30-Day Actions'},
    {key:'90',  label:'90-Day Actions'},
    {key:'365', label:'365-Day / 1-Year Actions'},
  ];
  const acc = document.getElementById('roadmap-accordions');
  if (!acc) return;
  acc.innerHTML = periods.filter(p => secs[p.key]).map((p) => `
    <div class="accordion">
      <button class="accordion-btn" onclick="toggleAccordion(this)">
        <span>${p.label}</span><span class="acc-chevron">▼</span>
      </button>
      <div class="accordion-body">
        ${markdownToHTML(secs[p.key])}
      </div>
    </div>`).join('');
}

function toggleAccordion(btn) {
  const body    = btn.nextElementSibling;
  const chevron = btn.querySelector('.acc-chevron');
  const isOpen  = body.classList.contains('open');

  // Close all accordions in the same container first
  const container = btn.closest('#roadmap-accordions');
  if (container) {
    container.querySelectorAll('.accordion-btn').forEach(b => {
      b.classList.remove('open');
      b.nextElementSibling.classList.remove('open');
      const c = b.querySelector('.acc-chevron');
      if (c) c.textContent = '▼';
    });
  }

  // Open the clicked one only if it was previously closed
  if (!isOpen) {
    body.classList.add('open');
    btn.classList.add('open');
    if (chevron) chevron.textContent = '▲';
  }
}

// ── TOOLTIP (why text on hover) ──────────────────────────────────────
(function initWhyTip() {
  const tip = document.createElement('div');
  tip.id = 'q-tip';
  document.body.appendChild(tip);
  let cur = null;
  document.addEventListener('mouseover', e => {
    const row = e.target.closest('.qb-row[data-why]');
    if (!row || !row.dataset.why) { tip.style.opacity = '0'; cur = null; return; }
    if (row === cur) return;
    cur = row;
    tip.textContent = row.dataset.why;
    const r = row.getBoundingClientRect();
    tip.style.opacity = '0';
    tip.style.left = r.left + 'px';
    tip.style.top = (r.bottom + window.scrollY + 6) + 'px';
    tip.style.width = r.width + 'px';
    requestAnimationFrame(() => tip.style.opacity = '1');
  });
  document.addEventListener('mouseout', e => {
    const row = e.target.closest('.qb-row[data-why]');
    if (!row) return;
    if (!e.relatedTarget || !e.relatedTarget.closest('.qb-row[data-why]')) {
      tip.style.opacity = '0'; cur = null;
    }
  });
})();

// ── INIT ─────────────────────────────────────────────────────────────
loadConfig();
