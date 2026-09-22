'use strict';

// ── STATE ─────────────────────────────────────────────────────────────
const STATE = { domain: '', type: '' };
const DOMAINS = ['Consent', 'Storage', 'Usage', 'Rights', 'Governance', 'Common'];
let _resources = [];

// ── INIT ──────────────────────────────────────────────────────────────
async function loadResources() {
  try {
    const r = await fetch('/api/method/dpdp_tool.api.get_resources', {
      headers: { 'Accept': 'application/json' }
    });
    const j = await r.json();
    _resources = j.message || [];
  } catch (e) {
    _resources = [];
  }

  const loading = document.getElementById('res-loading');
  if (loading) loading.remove();

  renderSidebarCounts();
  renderGrid();
}

// ── SIDEBAR COUNTS ────────────────────────────────────────────────────
function renderSidebarCounts() {
  const live = _resources.filter(r => !r.coming_soon);
  const el = document.getElementById('sb-count-all');
  if (el) el.textContent = live.length;
  DOMAINS.forEach(d => {
    const cel = document.getElementById('sb-count-' + d.toLowerCase());
    if (cel) cel.textContent = live.filter(r => r.domain === d).length;
  });
}

// ── RENDER ────────────────────────────────────────────────────────────
function renderGrid() {
  const filtered = applyFilters();
  const grid  = document.getElementById('res-grid');
  const empty = document.getElementById('res-empty');

  if (!filtered.length) {
    grid.style.display  = 'none';
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';
  grid.style.display  = 'block';

  const noFilter = !STATE.domain && !STATE.type;
  const featured = noFilter ? filtered.find(r => r.featured && !r.coming_soon) : null;
  const rest = filtered.filter(r => !featured || r.name !== featured.name);

  let html = '';
  if (featured) html += mkFeaturedCard(featured);

  DOMAINS.forEach(domain => {
    const group = rest.filter(r => r.domain === domain);
    if (!group.length) return;
    html += `<div class="res-section-hdr"><span class="res-section-lbl">${domain}</span><div class="res-section-line"></div></div>`;
    html += '<div class="res-grid-row">';
    group.forEach(r => { html += r.coming_soon ? mkSoonCard(r) : mkResourceCard(r); });
    html += '</div>';
  });

  const other = rest.filter(r => !DOMAINS.includes(r.domain));
  if (other.length) {
    html += `<div class="res-section-hdr"><span class="res-section-lbl">General</span><div class="res-section-line"></div></div>`;
    html += '<div class="res-grid-row">';
    other.forEach(r => { html += r.coming_soon ? mkSoonCard(r) : mkResourceCard(r); });
    html += '</div>';
  }

  grid.innerHTML = html;
}

// ── CARD TEMPLATES ────────────────────────────────────────────────
function mkFeaturedCard(r) {
  const cta = r.external_url
    ? `<a href="${r.external_url}" target="_blank" rel="noopener" class="rcard-cta">Read guide →</a>`
    : '';
  const time = r.read_time ? `<span class="rcard-time">⏱ ${r.read_time} min read</span>` : '';
  return `<div class="rcard rcard-featured">
    <div class="rcard-featured-body">
      <div class="rcard-meta">
        <span class="rcard-badge-featured">Start here</span>
        ${mkTypeBadge(r.resource_type)}
        <span class="rcard-domain-pill">${r.domain}</span>
      </div>
      <div class="rcard-title rcard-title-lg">${r.title}</div>
      <div class="rcard-desc">${r.summary}</div>
      <div class="rcard-footer-inline">${time}${cta}</div>
    </div>
    <div class="rcard-featured-visual" aria-hidden="true">
      <span class="rcard-featured-icon">📄</span>
    </div>
  </div>`;
}

function mkResourceCard(r) {
  const labels = { Guide: 'Read guide', Template: 'Download', Checklist: 'Open checklist', Video: 'Watch' };
  const dl = labels[r.resource_type] || 'Open';
  const time = r.read_time
    ? `<span class="rcard-time">⏱ ${r.read_time} min</span>`
    : r.resource_type === 'Template' ? `<span class="rcard-time">📥 Download</span>` : '';
  const cta = r.external_url
    ? `<a href="${r.external_url}" target="_blank" rel="noopener" class="rcard-cta">${dl} →</a>`
    : '';
  return `<div class="rcard">
    <div class="rcard-body">
      <div class="rcard-meta">
        ${mkTypeBadge(r.resource_type)}
        <span class="rcard-domain-pill">${r.domain}</span>
      </div>
      <div class="rcard-title">${r.title}</div>
      <div class="rcard-desc">${r.summary}</div>
    </div>
    <div class="rcard-footer">${time}${cta}</div>
  </div>`;
}

function mkSoonCard(r) {
  return `<div class="rcard rcard-soon">
    <div class="rcard-body">
      <div class="rcard-meta">
        <span class="rcard-soon-tag">Coming soon</span>
        ${mkTypeBadge(r.resource_type)}
      </div>
      <div class="rcard-title rcard-title-muted">${r.title}</div>
      <div class="rcard-desc rcard-desc-muted">${r.summary}</div>
    </div>
  </div>`;
}

function mkTypeBadge(type) {
  const cls = { Guide: 'type-guide', Template: 'type-template', Checklist: 'type-checklist', Video: 'type-video' }[type] || 'type-guide';
  return `<span class="rcard-type ${cls}">${type}</span>`;
}

// ── FILTERING ─────────────────────────────────────────────────────────
function applyFilters() {
  return _resources.filter(r => {
    if (STATE.domain && r.domain !== STATE.domain) return false;
    if (STATE.type   && r.resource_type !== STATE.type) return false;
    return true;
  });
}

function setFilter(key, value) {
  STATE[key] = STATE[key] === value ? '' : value;
  renderGrid();
  syncFilterUI();
}

function syncFilterUI() {
  document.querySelectorAll('.res-sb-link[data-domain]').forEach(el => {
    el.classList.toggle('active', el.dataset.domain === STATE.domain);
  });
  document.querySelectorAll('.res-sb-link[data-type]').forEach(el => {
    el.classList.toggle('active', el.dataset.type === STATE.type);
  });
}

function resetFilters() {
  STATE.domain = '';
  STATE.type   = '';
  syncFilterUI();
  renderGrid();
}

// ── EVENT WIRING ──────────────────────────────────────────────────────
function sidebarFilter(el, key) {
  const val = el.dataset[key] || '';
  setFilter(key, val);
}

// ── BOOT ──────────────────────────────────────────────────────────────
loadResources();
