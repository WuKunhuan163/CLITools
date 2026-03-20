function createModelInfoLine(provider, round, latency, model) {
  const name = resolveDisplayName(provider, model);
  const logo = resolveModelLogo(provider);
  const div = document.createElement('div');
  div.className = 'model-info';
  let html = logo ? `<img src="${logo}" alt="${name}">` : `<i class="bx bx-bot model-info-icon"></i>`;
  html += `<span class="model-name">${name}</span>`;
  if (round > 1) html += `<span class="model-sep">·</span><span class="model-round">round ${round}</span>`;
  if (latency) html += `<span class="model-sep">·</span><span class="model-latency">${latency}s</span>`;
  div.innerHTML = html;
  return div;
}

function toggleDebug() {
  debugMode = !debugMode;
  document.body.classList.toggle('debug-mode', debugMode);
  $('debug-toggle').classList.toggle('active', debugMode);
  engine.setDebugMode(debugMode, createDebugBlock);
  try { localStorage.setItem('debug_mode', debugMode ? '1' : '0'); } catch(e) {}
}
function setDebugModeTo(on) {
  debugMode = !!on;
  document.body.classList.toggle('debug-mode', debugMode);
  $('debug-toggle').classList.toggle('active', debugMode);
  engine.setDebugMode(debugMode, createDebugBlock);
  try { localStorage.setItem('debug_mode', debugMode ? '1' : '0'); } catch(e) {}
}
