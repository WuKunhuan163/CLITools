let THEMES = {
  dark: { label: 'Dark', icon: 'bx-moon', cls: '', favicon_color: '#5b8def' },
};
let BRILLIANT_PALETTES = [];
let currentTheme = localStorage.getItem('theme') || 'dark';
let currentPalette = localStorage.getItem('brilliantPalette') || 'strawberry';

async function _loadPalette() {
  try {
    const r = await fetch('/api/palette');
    const d = await r.json();
    if (!d.ok) return;
    if (d.themes && d.themes.length) {
      THEMES = {};
      for (const t of d.themes) {
        THEMES[t.id] = { label: t.label, icon: t.icon, cls: t.cls || '', favicon_color: t.favicon_color };
      }
    }
    if (d.palettes && d.palettes.length) {
      BRILLIANT_PALETTES = d.palettes.map(p => ({ id: p.id, icon: p.icon, label: p.label, favicon_color: p.favicon_color }));
    }
  } catch (e) { console.warn('Failed to load palette:', e); }
  if (!THEMES[currentTheme]) currentTheme = 'dark';
}

/* ── i18n ── */
let _I18N = {};
let _guiLang = localStorage.getItem('guiLang') || 'en';

async function _loadI18N() {
  try {
    const r = await fetch('/api/i18n');
    const d = await r.json();
    if (d.ok && d.translations) _I18N = d.translations;
  } catch (e) { console.warn('Failed to load i18n:', e); }
}

function _(key) {
  if (_guiLang === 'en' || !_I18N[_guiLang]) return key;
  return _I18N[_guiLang][key] || key;
}
function _applyLang() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = _(el.dataset.i18n);
  });
  const inp = $('input');
  if (inp) { inp.placeholder = _('Type a message. Ctrl+Enter to send.'); if (typeof _autoResizeInput === 'function') _autoResizeInput(); }
  _refreshPillLabels();
  renderSettingsTab();
}
function _refreshPillLabels() {
  if (typeof modePill !== 'undefined' && modePill) {
    modePill.setOptions(Object.keys(MODE_ICONS).map(k => ({ value: k, label: _(MODE_LABELS[k]), icon: MODE_ICONS[k] })));
  }
  if (typeof modelPill !== 'undefined' && modelPill) {
    modelPill.setOptions(MODEL_OPTIONS.map(o => {
      if (o.value === 'auto') return { value: 'auto', label: _('Auto'), icon: 'bx-bot', status: 'available' };
      const logo = o.logo || MODEL_LOGOS[o.value] || resolveModelLogo(o.value);
      return { value: o.value, label: _(o.label), status: o.status || 'available', ...(logo ? { logo } : { icon: 'bx-bot' }) };
    }));
  }
  if (turnLimitPill) turnLimitPill.render();
}

const _FAVICON_SVG = (color) => `data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2224%22 height=%2224%22 viewBox=%220 0 24 24%22 fill=%22${encodeURIComponent(color)}%22><path d=%22M21.928 11.607c-.202-.488-.635-.605-.928-.633V8c0-1.103-.897-2-2-2h-6V4.61c.305-.274.5-.668.5-1.11a1.5 1.5 0 0 0-3 0c0 .442.195.836.5 1.11V6H5c-1.103 0-2 .897-2 2v2.997l-.082.006A1 1 0 0 0 1.99 12v2a1 1 0 0 0 1 1H3v5c0 1.103.897 2 2 2h14c1.103 0 2-.897 2-2v-5a1 1 0 0 0 1-1v-1.938a1.006 1.006 0 0 0-.072-.455zM5 20V8h14l.001 3.996L19 12v2l.001.005.001 5.995H5z%22/><ellipse cx=%228.5%22 cy=%2212%22 rx=%221.5%22 ry=%222%22/><ellipse cx=%2215.5%22 cy=%2212%22 rx=%221.5%22 ry=%222%22/><path d=%22M8 16h8v2H8z%22/></svg>`;

function _updateFavicon() {
  let color;
  if (currentTheme === 'brilliant') {
    const pal = BRILLIANT_PALETTES.find(p => p.id === currentPalette);
    color = (pal && pal.favicon_color) || '#e85d75';
  } else {
    const t = THEMES[currentTheme];
    color = (t && t.favicon_color) || '#5b8def';
  }
  const link = document.getElementById('dynamic-favicon');
  if (link) link.href = _FAVICON_SVG(color);
}

function applyPalette(paletteId) {
  currentPalette = paletteId;
  localStorage.setItem('brilliantPalette', paletteId);
  BRILLIANT_PALETTES.forEach(p => document.body.classList.remove('palette-' + p.id));
  document.body.classList.add('palette-' + paletteId);
  const btn = $('palette-cycle-btn');
  if (btn) {
    const pal = BRILLIANT_PALETTES.find(p => p.id === paletteId);
    btn.textContent = pal ? pal.icon : '🍓';
    btn.title = pal ? pal.label : 'Strawberry';
  }
  _updateFavicon();
}
function cyclePalette() {
  const idx = BRILLIANT_PALETTES.findIndex(p => p.id === currentPalette);
  const next = BRILLIANT_PALETTES[(idx + 1) % BRILLIANT_PALETTES.length];
  applyPalette(next.id);
  renderSettingsTab();
}
function applyTheme(name) {
  currentTheme = name;
  document.body.classList.remove('light-mode', 'brilliant-mode', 'hacker-mode');
  BRILLIANT_PALETTES.forEach(p => document.body.classList.remove('palette-' + p.id));
  if (THEMES[name]?.cls) document.body.classList.add(THEMES[name].cls);
  if (name === 'brilliant') applyPalette(currentPalette);
  const icon = $('theme-icon');
  if (icon) icon.className = 'bx ' + (THEMES[name]?.icon || 'bx-moon');
  localStorage.setItem('theme', name);
  _updateFavicon();
  _adaptLogoBrightness();
  const overlay = $('settings-overlay');
  if (overlay && overlay.classList.contains('open')) renderSettingsTab();
}

const _logoAdaptCache = new Map();
function _getBgBrightness() {
  const s = getComputedStyle(document.body);
  const bg = s.getPropertyValue('--bg').trim();
  const m = bg.match(/^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})/i);
  if (!m) return 0.1;
  const r = parseInt(m[1], 16), g = parseInt(m[2], 16), b = parseInt(m[3], 16);
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255;
}

function _adaptLogoBrightness() {
  const bgBright = _getBgBrightness();
  const isDarkBg = bgBright < 0.5;
  document.querySelectorAll('img.logo-adaptive').forEach(img => {
    if (!img.complete || !img.naturalWidth) {
      img.onload = () => _adaptSingleLogo(img, isDarkBg);
      return;
    }
    _adaptSingleLogo(img, isDarkBg);
  });
}

function _adaptSingleLogo(img, isDarkBg) {
  const declared = img.dataset.logoBrightness;
  if (declared !== undefined && declared !== '') {
    const lb = parseFloat(declared);
    if (!isNaN(lb)) {
      _applyLogoFilter(img, lb, isDarkBg);
      return;
    }
  }
  const src = img.src;
  if (_logoAdaptCache.has(src)) {
    _applyLogoFilter(img, _logoAdaptCache.get(src), isDarkBg);
    return;
  }
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  const w = Math.min(img.naturalWidth, 64);
  const h = Math.min(img.naturalHeight, 64);
  canvas.width = w;
  canvas.height = h;
  try {
    ctx.drawImage(img, 0, 0, w, h);
    const data = ctx.getImageData(0, 0, w, h).data;
    let totalBright = 0, count = 0;
    for (let i = 0; i < data.length; i += 4) {
      if (data[i + 3] < 30) continue;
      totalBright += (0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]) / 255;
      count++;
    }
    const logoBright = count > 0 ? totalBright / count : 0.5;
    _logoAdaptCache.set(src, logoBright);
    _applyLogoFilter(img, logoBright, isDarkBg);
  } catch (e) {
    _logoAdaptCache.set(src, -1);
    img.style.filter = '';
  }
}

function _applyLogoFilter(img, logoBright, isDarkBg) {
  if (logoBright < 0) { img.style.filter = ''; return; }
  const isLogoDark = logoBright < 0.35;
  const isLogoLight = logoBright > 0.7;
  if (isDarkBg && isLogoDark) {
    img.style.filter = 'invert(1)';
  } else if (!isDarkBg && isLogoLight) {
    img.style.filter = 'invert(1)';
  } else {
    img.style.filter = '';
  }
}

function cycleTheme() {
  const keys = Object.keys(THEMES);
  const next = keys[(keys.indexOf(currentTheme) + 1) % keys.length];
  applyTheme(next);
  if (settingsTab === 'general') renderSettingsTab();
}

/* Apply default theme immediately for loading-gate; re-applied after _loadPalette() */
if (THEMES[currentTheme]?.cls) document.body.classList.add(THEMES[currentTheme].cls);
