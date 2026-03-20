function _preloadIcon(url) {
  if (!url || _iconCache[url]) return;
  const img = new Image();
  img.src = url;
  _iconCache[url] = img;
}

async function _loadModelsMeta() {
  try {
    const r = await fetch('/api/models/metadata');
    const d = await r.json();
    if (!d.ok) return;
    if (d.providers) {
      for (const [pid, p] of Object.entries(d.providers)) {
        if (p.icon) { PROVIDER_LOGOS[pid] = p.icon; _preloadIcon(p.icon); }
      }
      PROVIDER_LOGOS['github-copilot'] = PROVIDER_LOGOS['copilot'] || null;
    }
    if (d.models) {
      for (const [mid, m] of Object.entries(d.models)) {
        if (m.icon) { MODEL_LOGOS[mid] = m.icon; _preloadIcon(m.icon); }
        if (m.display_name) MODEL_DISPLAY_NAMES[mid] = m.display_name;
      }
    }
    if (d.env) {
      for (const [eid, e] of Object.entries(d.env)) {
        if (e.icon) { ENV_LOGOS[eid] = e.icon; _preloadIcon(e.icon); }
        if (e.display_name) MODEL_DISPLAY_NAMES[eid] = e.display_name;
      }
    }
    if (d.modes) {
      for (const [mid, m] of Object.entries(d.modes)) {
        if (m.icon) MODE_ICONS[mid] = m.icon;
        if (m.label) MODE_LABELS[mid] = m.label;
      }
    }
  } catch (e) { console.warn('Failed to load models metadata:', e); }
}

function resolveDisplayName(provider, model) {
  if (AI_IDE_PROVIDERS.has(provider) && model) {
    const baseName = MODEL_DISPLAY_NAMES[provider] || provider;
    return `${baseName} (${model})`;
  }
  return MODEL_DISPLAY_NAMES[provider] || provider;
}

function resolveModelLogo(provider) {
  if (MODEL_LOGOS[provider]) return MODEL_LOGOS[provider];
  const vendor = (provider || '').split('-')[0];
  if (PROVIDER_LOGOS[vendor]) return PROVIDER_LOGOS[vendor];
  return null;
}

let MODEL_OPTIONS = [
  { value: 'auto', label: 'Auto' },
];
