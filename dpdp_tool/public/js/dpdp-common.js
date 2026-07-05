'use strict';

// ── SHARED PROFILE STORE ──────────────────────────────────────────────
// Cross-form pre-fill: assessment intro ↔ consult request form.
// Key is not email-scoped — it holds the most recently confirmed profile.

const PROFILE_KEY = 'dpdp_last_profile';

function saveProfile(data) {
  try { localStorage.setItem(PROFILE_KEY, JSON.stringify(data)); } catch(e) {}
}

function loadProfile() {
  try {
    const raw = localStorage.getItem(PROFILE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch(e) { return null; }
}

// fieldMap: { profileKey: elementId, ... }
// Only fills empty fields so user edits are never overwritten.
function prefillFormFromProfile(fieldMap) {
  const p = loadProfile();
  if (!p) return;
  Object.entries(fieldMap).forEach(([key, id]) => {
    if (!p[key]) return;
    const el = document.getElementById(id);
    if (el && !el.value) el.value = p[key];
  });
}
