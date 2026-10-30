'use strict';

// ── STATE ─────────────────────────────────────────────────────────────
const EV_STATE = { type: '', status: '' };
const EV_TYPE_BADGE = { Event: 'type-guide', Workshop: 'type-template', Webinar: 'type-video' };
const EV_HERO_MAX = 3;
const EV_AVATAR_TINTS = ['type-guide', 'type-checklist', 'type-template', 'type-video'];
let _events = [];

// ── INIT ──────────────────────────────────────────────────────────────
async function loadEvents() {
  try {
    const r = await fetch('/api/method/dpdp_tool.api.get_events', {
      headers: { 'Accept': 'application/json' }
    });
    const j = await r.json();
    _events = j.message || [];
  } catch (e) {
    _events = [];
  }

  const loading = document.getElementById('ev-loading');
  if (loading) loading.remove();

  renderHero();
  renderTimeline();
}

// ── HELPERS ───────────────────────────────────────────────────────────
function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

function safeUrl(u) {
  return /^https?:\/\//i.test(u || '') ? esc(u) : '';
}

function dateLabel(ev) {
  if (ev.date_label) return ev.date_label;
  if (!ev.event_date) return 'Date to confirm';
  const d = new Date(ev.event_date + 'T00:00:00');
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

function linkedinUrl(u) {
  return /^https:\/\/([a-z]{2,3}\.)?linkedin\.com\//i.test(u || '') ? esc(u) : '';
}

function initials(name) {
  const parts = String(name || '').trim().split(/\s+/);
  return ((parts[0] || '')[0] || '') + (parts.length > 1 ? parts[parts.length - 1][0] : '');
}

function joinNames(names) {
  return names.length < 2 ? names.join('') : names.slice(0, -1).join(', ') + ' and ' + names[names.length - 1];
}

// Luma-style: overlapping initials, then "With A, B and C" (names link to LinkedIn)
function mkSpeakers(speakers) {
  if (!speakers || !speakers.length) return '';
  const avs = speakers.map((sp, i) =>
    `<span class="ev-av rcard-type ${EV_AVATAR_TINTS[i % EV_AVATAR_TINTS.length]}">${esc(initials(sp.speaker_name).toUpperCase())}</span>`
  ).join('');
  const names = speakers.map(sp => {
    const li = linkedinUrl(sp.linkedin_url);
    return li ? `<a href="${li}" target="_blank" rel="noopener">${esc(sp.speaker_name)}</a>` : `<b>${esc(sp.speaker_name)}</b>`;
  });
  return `<div class="ev-speakers">
          <span class="ev-avs" aria-hidden="true">${avs}</span>
          <span class="ev-names">With ${joinNames(names)}</span>
        </div>`;
}

// ── HERO (What's coming up) ───────────────────────────────────────────
function renderHero() {
  const list = document.getElementById('ev-hero-list');
  if (!list) return;
  const picks = _events
    .filter(ev => ev.show_in_hero && ev.status === 'Upcoming')
    // soonest first; undated (tentative month) ones sort ahead of dated ones
    .sort((a, b) => (a.event_date || '').localeCompare(b.event_date || ''))
    .slice(0, EV_HERO_MAX);
  // above the static Cohort 2 row, which is the furthest out
  list.insertAdjacentHTML('afterbegin', picks.map(ev => `<div class="tl">
      <div class="tl-d"><strong>${esc(dateLabel(ev))}</strong>${esc(ev.event_type)}</div>
      <div>
        <span class="badge b-come">UPCOMING</span>
        <div class="tl-lbl">${esc(ev.title)}</div>
        <div class="tl-desc">${esc(ev.location)}</div>
      </div>
    </div>`).join(''));
}

// ── TIMELINE ──────────────────────────────────────────────────────────
function renderTimeline() {
  const filtered = _events.filter(ev => {
    if (EV_STATE.type && ev.event_type !== EV_STATE.type) return false;
    if (EV_STATE.status && ev.status !== EV_STATE.status) return false;
    return true;
  });
  document.getElementById('ev-empty').hidden = filtered.length > 0;
  document.getElementById('ev-timeline').innerHTML = filtered.map(mkEventRow).join('');
}

function mkEventRow(ev) {
  const upcoming = ev.status === 'Upcoming';
  const badge = EV_TYPE_BADGE[ev.event_type] || 'type-guide';
  const where = [ev.location, ev.participants].filter(Boolean).map(esc).join(' · ');
  const reg = upcoming && safeUrl(ev.register_url)
    ? `<a class="btn-o" href="${safeUrl(ev.register_url)}" target="_blank" rel="noopener">Register</a>` : '';
  const slides = safeUrl(ev.slides_url)
    ? `<a class="rcard-cta" href="${safeUrl(ev.slides_url)}" target="_blank" rel="noopener">View slides →</a>` : '';

  return `<div class="ev-row">
    <div class="ev-date">
      <div class="ev-day">${esc(dateLabel(ev))}</div>
      <div class="ev-dsub">${esc(ev.date_note || ev.status)}</div>
    </div>
    <div class="ev-rail" aria-hidden="true"></div>
    <article class="rcard">
      <div class="rcard-body">
        <div class="rcard-meta">
          <span class="rcard-type ${badge}">${esc(ev.event_type)}</span>
          <span class="rcard-domain-pill">${esc(ev.status)}</span>
          ${ev.format ? `<span class="rcard-domain-pill">${esc(ev.format)}</span>` : ''}
        </div>
        <h3 class="rcard-title rcard-title-lg">${esc(ev.title)}</h3>
        ${ev.partner ? `<div class="rcard-time">${esc(ev.partner)}</div>` : ''}
        ${mkSpeakers(ev.speakers)}
        <p class="rcard-desc">${esc(ev.summary)}</p>
      </div>
      ${where || reg || slides ? `<div class="rcard-footer">
        <span class="rcard-time">${where}</span>
        <span class="ev-actions">${slides}${reg}</span>
      </div>` : ''}
    </article>
  </div>`;
}

// ── FILTERS ───────────────────────────────────────────────────────────
function setEventFilter(el) {
  EV_STATE[el.dataset.key] = el.dataset.value;
  syncEventFilterUI();
  renderTimeline();
}

function resetEventFilters() {
  EV_STATE.type = '';
  EV_STATE.status = '';
  syncEventFilterUI();
  renderTimeline();
}

function syncEventFilterUI() {
  document.querySelectorAll('.ev-chip').forEach(el => {
    const on = EV_STATE[el.dataset.key] === el.dataset.value;
    el.classList.toggle('active', on);
    el.setAttribute('aria-pressed', on);
  });
}

// ── BOOT ──────────────────────────────────────────────────────────────
loadEvents();
