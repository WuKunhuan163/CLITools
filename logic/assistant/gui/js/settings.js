/* ── Settings Panel ── */
let settingsTab = 'general';
let usageData = { models: {}, providers: {}, calls: [], rates: {} };
let displayCurrency = localStorage.getItem('displayCurrency') || 'USD';
let currencyList = [];

function openSettings(tab) {
  if (tab) { settingsTab = tab; }
  $('settings-overlay').classList.add('open');
  fetchUsageData().then(() => {
    document.querySelectorAll('.settings-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === settingsTab));
    renderSettingsTab();
  });
}
function closeSettings() {
  $('settings-overlay').classList.remove('open');
}
function switchSettingsTab(tab) {
  settingsTab = tab;
  document.querySelectorAll('.settings-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
  renderSettingsTab();
}

async function fetchUsageData() {
  try {
    const resp = await fetch('/api/usage');
    const data = await resp.json();
    if (data.ok) usageData = data.usage || usageData;
  } catch (e) { console.warn('Usage fetch failed:', e); }
}

function renderSettingsTab() {
  const el = $('settings-content');
  if (settingsTab === 'general') {
    el.innerHTML = renderGeneralView();
  } else if (settingsTab === 'chat') {
    el.innerHTML = '<div style="padding:24px;color:var(--text-3)">Loading...</div>';
    renderChatView().then(html => el.innerHTML = html);
  } else if (settingsTab === 'models') {
    el.innerHTML = renderModelsView();
  } else if (settingsTab === 'brain') {
    el.innerHTML = '<div style="padding:24px;color:var(--text-3)">Loading...</div>';
    renderBrainView().then(html => el.innerHTML = html);
  } else if (settingsTab === 'permissions') {
    el.innerHTML = '<div style="padding:24px;color:var(--text-3)">Loading...</div>';
    renderPermissionsView().then(html => el.innerHTML = html);
  } else if (settingsTab === 'data') {
    el.innerHTML = '<div style="padding:24px;color:var(--text-3)">Loading...</div>';
    renderDataView().then(html => el.innerHTML = html);
  } else {
    el.innerHTML = renderProvidersView();
  }
}

function _settingsNumInput(key, defaultVal, min, max, desc, mode) {
  const saved = localStorage.getItem(key);
  const val = saved ? parseInt(saved) : defaultVal;
  const fmtK = (n) => n >= 1048576 ? Math.floor(n/1048576)+'m' : n >= 1024 ? Math.floor(n/1024)+'k' : String(Math.floor(n));
  const resolvedMode = mode || (defaultVal >= 256 ? 'pow2' : 'linear');
  const step = defaultVal >= 1000 ? 1000 : defaultVal >= 100 ? 100 : defaultVal >= 10 ? 5 : 1;
  const displayVal = resolvedMode === 'pow2' ? fmtK(val) : String(val);
  return `<label style="display:flex;align-items:center;gap:8px;font-size:13px;margin-bottom:10px;">
    <span style="flex:1"><strong>${key.replace(/_/g,' ').replace(/\b\w/g,l=>l.toUpperCase())}</strong><br><span style="color:var(--text-3);font-size:11.5px;">${desc}</span></span>
    <div class="settings-stepper" data-key="${key}" data-min="${min}" data-max="${max}" data-default="${defaultVal}" data-mode="${resolvedMode}" data-step="${step}" title="${fmtK(val)}">
      <button class="stepper-btn down" onclick="_stepperClick(this,-1)">\u25BC</button>
      <span class="stepper-value">${displayVal}</span>
      <button class="stepper-btn up" onclick="_stepperClick(this,1)">\u25B2</button>
    </div>
  </label>`;
}

function _stepperClick(btn, dir) {
  const wrapper = btn.closest('.settings-stepper');
  const key = wrapper.dataset.key;
  const min = parseInt(wrapper.dataset.min);
  const max = parseInt(wrapper.dataset.max);
  const def = parseInt(wrapper.dataset.default);
  const mode = wrapper.dataset.mode;
  const valEl = wrapper.querySelector('.stepper-value');
  const fmtK = (n) => n >= 1048576 ? Math.floor(n/1048576)+'m' : n >= 1024 ? Math.floor(n/1024)+'k' : String(Math.floor(n));

  let raw = parseInt(localStorage.getItem(key)) || def;
  if (mode === 'pow2') {
    raw = dir > 0 ? Math.min(raw * 2, max) : Math.max(Math.floor(raw / 2), min);
    valEl.textContent = fmtK(raw);
    wrapper.title = fmtK(raw);
  } else {
    const step = parseInt(wrapper.dataset.step) || 1;
    raw = dir > 0 ? Math.min(raw + step, max) : Math.max(raw - step, min);
    valEl.textContent = raw;
  }
  localStorage.setItem(key, raw);
  _saveAssistantConfig(key, raw);
}

async function _saveAssistantConfig(key, value) {
  try {
    await fetch('/api/send', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({_config: true, key, value}) });
  } catch(e) {}
}

function _currencyOpts() {
  if (!currencyList.length) {
    const info = usageData.rates || {};
    const codes = Object.keys(info).sort();
    const top = ['USD','EUR','GBP','CNY','JPY','KRW','INR','CAD','AUD','CHF','HKD','SGD','TWD','BRL'];
    const topCodes = top.filter(c => info[c]);
    const restCodes = codes.filter(c => !top.includes(c));
    currencyList = [...topCodes, ...restCodes];
  }
  return currencyList.map(c => {
    const info = (usageData.rates || {})[c];
    const sym = info ? info.symbol : c;
    const label = sym !== c ? `${c} (${sym})` : c;
    return `<option value="${c}" ${c === displayCurrency ? 'selected' : ''}>${label}</option>`;
  }).join('');
}
function _setCurrency(code) {
  displayCurrency = code;
  localStorage.setItem('displayCurrency', code);
  renderSettingsTab();
}
function renderGeneralView() {
  const themeOpts = Object.entries(THEMES).map(([k, v]) =>
    `<option value="${k}" ${k === currentTheme ? 'selected' : ''}>${v.label}</option>`
  ).join('');
  const currentLang = localStorage.getItem('guiLang') || 'en';
  const langOpts = [
    { value: 'en', label: 'English' },
    { value: 'zh', label: '中文' },
    { value: 'ar', label: 'العربية' },
  ].map(l => `<option value="${l.value}" ${l.value === currentLang ? 'selected' : ''}>${l.label}</option>`).join('');
  return `<div class="settings-section-title">${_('Appearance')}</div>
    <div class="settings-card" style="padding:16px;">
      <div style="display:flex;align-items:center;gap:12px;font-size:13px;margin-bottom:12px;">
        <span><strong>${_('Color Mode')}</strong></span>
        <select onchange="applyTheme(this.value)" style="background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:6px 10px;color:var(--text);font-size:13px;font-family:var(--font);cursor:pointer;min-width:120px;">${themeOpts}</select>
        ${currentTheme === 'brilliant' ? `<button id="palette-cycle-btn" onclick="cyclePalette()" style="background:var(--surface-2);border:1px solid var(--border);border-radius:6px;padding:5px 10px;cursor:pointer;font-size:16px;line-height:1;" title="${(BRILLIANT_PALETTES.find(p=>p.id===currentPalette)||{}).label||'Strawberry'}">${(BRILLIANT_PALETTES.find(p=>p.id===currentPalette)||{}).icon||'🍓'}</button>` : ''}
      </div>
      <div style="display:flex;align-items:center;gap:12px;font-size:13px;margin-bottom:12px;">
        <span><strong>${_('Language')}</strong></span>
        <select onchange="_guiLang=this.value;localStorage.setItem('guiLang',this.value);_applyLang();" style="background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:6px 10px;color:var(--text);font-size:13px;font-family:var(--font);cursor:pointer;min-width:120px;">${langOpts}</select>
      </div>
      <div style="display:flex;align-items:center;gap:12px;font-size:13px;margin-bottom:12px;">
        <span><strong>${_('Currency')}</strong></span>
        <select id="currency-select" onchange="_setCurrency(this.value)" style="background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:6px 10px;color:var(--text);font-size:13px;font-family:var(--font);cursor:pointer;min-width:180px;">${_currencyOpts()}</select>
      </div>
    </div>
    <div class="settings-section-title" style="margin-top:16px;">${_('Behavior')}</div>
    <div class="settings-card" style="padding:16px;">
      <label style="display:flex;align-items:center;gap:12px;font-size:13px;margin-bottom:10px;">
        <span style="flex:1"><strong>${_('Default Round Limit')}</strong><br><span style="color:var(--text-3);font-size:11.5px;">Default max agent rounds for new tasks. None = unlimited.</span></span>
        <select onchange="const v=this.value==='0'?0:parseInt(this.value);localStorage.setItem('default_turn_limit',this.value);selectedTurnLimit=v;if(turnLimitPill)turnLimitPill.setValue(v);_saveAssistantConfig('default_turn_limit',v);" style="background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:6px 10px;color:var(--text);font-size:13px;font-family:var(--font);cursor:pointer;min-width:100px;">
          ${[1,2,5,10,20,50,100,200,500,0].map(v => `<option value="${v}" ${v === (parseInt(localStorage.getItem('default_turn_limit'))||20) ? 'selected' : ''}>${v === 0 ? 'None' : v + ' rounds'}</option>`).join('')}
        </select>
      </label>
      <label style="display:flex;align-items:center;gap:12px;font-size:13px;margin-bottom:10px;">
        <span style="flex:1"><strong>${_('History Round Folding')}</strong><br><span style="color:var(--text-3);font-size:11.5px;">Number of recent rounds to show before folding older ones.</span></span>
        <select onchange="INITIAL_ROUNDS=parseInt(this.value)||5;localStorage.setItem('initial_rounds',this.value);" style="background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:6px 10px;color:var(--text);font-size:13px;font-family:var(--font);cursor:pointer;min-width:100px;">
          ${[2,5,10,20,50,100].map(v => `<option value="${v}" ${v === INITIAL_ROUNDS ? 'selected' : ''}>${v} rounds</option>`).join('')}
        </select>
      </label>
      <div style="display:flex;align-items:center;gap:12px;font-size:13px;margin-bottom:10px;">
        <span style="flex:1"><strong>${_('Auto-scroll Idle')}</strong><br><span style="color:var(--text-3);font-size:11.5px;">Auto-scroll to bottom after inactivity. None to disable.</span></span>
        <select onchange="const v=this.value==='none'?0:parseInt(this.value);_autoScrollIdleS=v;localStorage.setItem('auto_scroll_idle_s',this.value);" style="background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:6px 10px;color:var(--text);font-size:13px;font-family:var(--font);cursor:pointer;min-width:100px;">
          ${[{v:'5',l:'5s'},{v:'10',l:'10s'},{v:'20',l:'20s'},{v:'60',l:'1 min'},{v:'120',l:'2 min'},{v:'300',l:'5 min'},{v:'none',l:'None'}].map(o => `<option value="${o.v}" ${(o.v==='none'?_autoScrollIdleS===0:parseInt(o.v)===_autoScrollIdleS) ? 'selected' : ''}>${o.l}</option>`).join('')}
        </select>
      </div>
      <div style="display:flex;align-items:center;gap:12px;font-size:13px;">
        <span style="flex:1"><strong>${_('Workspace')}</strong><br><span style="color:var(--text-3);font-size:11.5px;">Working directory for new sessions. Empty = project root.</span></span>
        <div style="display:flex;gap:4px;align-items:center;">
        <input id="workspace-input" type="text" value="${currentWorkspace||''}" placeholder="(project root)"
          onchange="setWorkspace(this.value)"
          style="background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:6px 10px;color:var(--text);font-size:12px;font-family:var(--font-mono);width:170px;outline:none;">
        <button onclick="browseWorkspaceDir()" title="Browse..."
          style="background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:5px 8px;color:var(--text-2);font-size:13px;cursor:pointer;line-height:1;"><i class="bx bx-folder-open"></i></button>
        </div>
      </div>
    </div>`;
}

const BENCH_SHORT = {
  'artificial_analysis_intelligence_index': 'INT',
  'artificial_analysis_coding_index': 'CODE',
  'artificial_analysis_math_index': 'MATH',
  'gpqa': 'GPQA', 'hle': 'HLE', 'mmlu_pro': 'MMLU-P',
  'math_500': 'MATH500', 'aime': 'AIME', 'aime_25': 'AIME25',
  'livecodebench': 'LCB', 'scicode': 'SCI', 'lcr': 'LCR',
  'ifbench': 'IF', 'tau2': 'TAU2', 'terminalbench_hard': 'TERM',
};
const BENCH_LABELS = {
  'artificial_analysis_intelligence_index': 'AA Intelligence Index',
  'artificial_analysis_coding_index': 'AA Coding Index',
  'artificial_analysis_math_index': 'AA Math Index',
  'gpqa': 'GPQA Diamond', 'hle': "Humanity's Last Exam",
  'mmlu_pro': 'MMLU Pro', 'math_500': 'MATH 500',
  'aime': 'AIME 2024', 'aime_25': 'AIME 2025',
  'livecodebench': 'LiveCodeBench', 'scicode': 'SciCode',
  'lcr': 'LCR', 'ifbench': 'IFBench',
  'tau2': 'TAU-2', 'terminalbench_hard': 'TerminalBench Hard',
};

function openBenchOverlay(modelName, event) {
  if (event) event.stopPropagation();
  const models = usageData.models || {};
  const m = models[modelName];
  if (!m) return;
  const aa = m.aa_benchmarks || {};
  const aaRank = m.aa_rankings || {};
  const entries = Object.entries(aaRank)
    .filter(([k]) => !k.startsWith('_') && aa[k] != null)
    .sort((a, b) => a[1] - b[1]);
  if (!entries.length) return;

  const _rankColor = (r) => {
    if (!r) return 'var(--surface-3);color:var(--text-3)';
    if (r <= 3) return r === 1 ? 'linear-gradient(135deg,#FFD700,#FFA500);color:#000' : r === 2 ? 'linear-gradient(135deg,#C0C0C0,#E8E8E8);color:#333' : 'linear-gradient(135deg,#CD7F32,#E8A862);color:#fff';
    if (r <= 5) return 'var(--purple-dim);color:var(--purple)';
    if (r <= 10) return 'var(--accent-dim);color:var(--accent)';
    return 'var(--surface-3);color:var(--text-3)';
  };

  let html = `<div style="display:flex;flex-wrap:wrap;gap:6px;">`;
  for (const [benchKey, rank] of entries) {
    const val = aa[benchKey];
    const fVal = typeof val === 'number' ? (val >= 10 ? val.toFixed(1) : val.toFixed(3)) : val;
    const label = BENCH_LABELS[benchKey] || benchKey;
    const short = BENCH_SHORT[benchKey] || benchKey;
    html += `<span class="settings-badge" style="background:${_rankColor(rank)};cursor:pointer;font-size:11px;padding:4px 10px;" onclick="openBenchChart('${esc(benchKey)}',event)" title="${label}: ${fVal} (rank #${rank})">${short} ${fVal} (#${rank})</span>`;
  }
  html += `</div>`;

  const displayName = modelName.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  showSubPanel('bench_' + modelName, displayName + ' — Benchmarks', html);
}

function openBenchChart(benchKey, event) {
  if (event) event.stopPropagation();
  const models = usageData.models || {};
  const label = BENCH_LABELS[benchKey] || benchKey;
  const entries = [];
  for (const [mid, m] of Object.entries(models)) {
    const val = (m.aa_benchmarks || {})[benchKey];
    const rank = (m.aa_rankings || {})[benchKey];
    if (val != null) {
      const dname = mid.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
      entries.push({ name: dname, value: val, rank: rank || 999 });
    }
  }
  if (!entries.length) return;
  entries.sort((a, b) => b.value - a.value);

  const cId = 'bench_chart_' + benchKey.replace(/[^a-z0-9]/gi, '_');
  let html = `<canvas id="${cId}" style="width:100%;max-height:300px;"></canvas>`;
  showSubPanel('chart_' + benchKey, label, html, () => {
    const canvas = document.getElementById(cId);
    if (!canvas) return;
    const colors = entries.map(e =>
      e.rank === 1 ? '#FFD700' : e.rank === 2 ? '#C0C0C0' : e.rank === 3 ? '#CD7F32' : 'var(--accent)');
    new Chart(canvas, {
      type: 'bar',
      data: {
        labels: entries.map(e => e.name),
        datasets: [{ data: entries.map(e => e.value), backgroundColor: colors, borderWidth: 0 }]
      },
      options: {
        indexAxis: 'y', responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, title: { display: true, text: label, color: getComputedStyle(document.body).getPropertyValue('--text').trim() } },
        scales: {
          x: { grid: { color: 'rgba(128,128,128,0.1)' }, ticks: { color: getComputedStyle(document.body).getPropertyValue('--text-2').trim() } },
          y: { grid: { display: false }, ticks: { color: getComputedStyle(document.body).getPropertyValue('--text-2').trim(), font: { size: 10 } } }
        }
      }
    });
  });
}

function showSubPanel(id, title, bodyHtml, afterRender) {
  const existing = document.querySelector(`.sub-overlay[data-panel-id="${id}"]`);
  if (existing) existing.remove();
  const overlay = document.createElement('div');
  overlay.className = 'sub-overlay';
  overlay.dataset.panelId = id;
  overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
  overlay.innerHTML = `
    <div class="sub-panel" style="width:440px;max-height:500px;">
      <div class="sub-panel-header"><span>${title}</span><button onclick="this.closest('.sub-overlay').remove()" style="background:none;border:none;color:var(--text-3);cursor:pointer;font-size:16px;"><i class="bx bx-x"></i></button></div>
      <div style="padding:14px;overflow-y:auto;flex:1;">${bodyHtml}</div>
    </div>`;
  document.body.appendChild(overlay);
  if (afterRender) setTimeout(afterRender, 50);
}

async function renderChatView() {
  let sbState = {};
  try {
    const sbRes = await fetch('/api/sandbox/state');
    sbState = await sbRes.json();
  } catch(e) {}
  const _cs = (window._sessionSettingsSchema || []).reduce((m,s)=>(m[s.key]=s,m),{});
  const crSchema = _cs['compression_ratio'] || {default:0.5,min:0.25,max:0.75,step:0.05};
  const clSchema = _cs['context_lines'] || {default:2,options:[0,1,2,5,10]};
  const savedRatio = parseFloat(localStorage.getItem('compression_ratio')) || crSchema.default;
  const maxCtx = engine._rawMaxContextTokens || engine._maxContextTokens || 0;
  const effectiveLimit = maxCtx ? Math.round(maxCtx * savedRatio) : 0;
  const limitLabel = effectiveLimit > 0
    ? `${(effectiveLimit/1000).toFixed(1)}k tokens (${(maxCtx/1000).toFixed(0)}k × ${(savedRatio*100).toFixed(0)}%)`
    : 'N/A';
  const ctxLines = parseInt(localStorage.getItem('context_lines')) || clSchema.default;
  return `
    <div class="settings-section-title">${_('Context Compression')}</div>
    <div class="settings-card" style="padding:16px;">
      <label style="display:flex;align-items:center;gap:12px;font-size:13px;">
        <span style="flex:1">
          <strong>${_('Compression Trigger')}</strong><br>
          <span style="color:var(--text-3);font-size:11.5px;">
            Compress context when it reaches this % of the model's max context window.
            When triggered, conversation history is summarized to free space. The ctx% per round is based on this limit.
          </span>
        </span>
        <div class="settings-stepper" id="compression-ratio-stepper" data-key="compression_ratio" data-min="${Math.round(crSchema.min*100)}" data-max="${Math.round(crSchema.max*100)}" data-default="${Math.round(crSchema.default*100)}" data-mode="linear" data-step="${Math.round((crSchema.step||0.05)*100)}">
          <button class="stepper-btn down" onclick="_compressionStep(-1)">&#x25BC;</button>
          <span class="stepper-value" id="compression-ratio-val">${(savedRatio*100).toFixed(0)}%</span>
          <button class="stepper-btn up" onclick="_compressionStep(1)">&#x25B2;</button>
        </div>
      </label>
    </div>

    <div class="settings-section-title">${_('Display')}</div>
    <div class="settings-card" style="padding:16px;">
      <label style="display:flex;align-items:center;gap:12px;font-size:13px;">
        <span style="flex:1">
          <strong>${_('Context Lines')}</strong><br>
          <span style="color:var(--text-3);font-size:11.5px;">
            Number of surrounding context lines shown around diffs and file reads.
          </span>
        </span>
        <div class="settings-stepper" id="ctx-lines-stepper">
          <button class="stepper-btn down" onclick="_ctxLinesStep(-1)">&#x25BC;</button>
          <span class="stepper-value" id="ctx-lines-val">${ctxLines}</span>
          <button class="stepper-btn up" onclick="_ctxLinesStep(1)">&#x25B2;</button>
        </div>
      </label>
      <label style="display:flex;align-items:center;gap:12px;font-size:13px;margin-top:10px;">
        <span style="flex:1">
          <strong>${_('Collapsed Lines')}</strong><br>
          <span style="color:var(--text-3);font-size:11.5px;">
            Lines visible when a tool output block is collapsed.
          </span>
        </span>
        <div class="settings-stepper" id="collapsed-lines-stepper">
          <button class="stepper-btn down" onclick="_blockLinesStep('block_collapsed_lines',-1)">&#x25BC;</button>
          <span class="stepper-value" id="collapsed-lines-val">${parseInt(localStorage.getItem('block_collapsed_lines'))||6}</span>
          <button class="stepper-btn up" onclick="_blockLinesStep('block_collapsed_lines',1)">&#x25B2;</button>
        </div>
      </label>
      <label style="display:flex;align-items:center;gap:12px;font-size:13px;margin-top:10px;">
        <span style="flex:1">
          <strong>${_('Expanded Lines')}</strong><br>
          <span style="color:var(--text-3);font-size:11.5px;">
            Lines visible when a tool output block is expanded (scroll for more).
          </span>
        </span>
        <div class="settings-stepper" id="expanded-lines-stepper">
          <button class="stepper-btn down" onclick="_blockLinesStep('block_expanded_lines',-1)">&#x25BC;</button>
          <span class="stepper-value" id="expanded-lines-val">${parseInt(localStorage.getItem('block_expanded_lines'))||16}</span>
          <button class="stepper-btn up" onclick="_blockLinesStep('block_expanded_lines',1)">&#x25B2;</button>
        </div>
      </label>
    </div>

    <div class="settings-section-title">${_('Data Retention')}</div>
    <div class="settings-card" style="padding:16px;">
      <label style="display:flex;align-items:center;gap:12px;font-size:13px;">
        <span style="flex:1">
          <strong>${_('History Context Rounds')}</strong><br>
          <span style="color:var(--text-3);font-size:11.5px;">
            Number of recent rounds whose full data is protected from cleanup. These rounds are retained for prompt engineering context.
          </span>
        </span>
        <select onchange="const v=parseInt(this.value);localStorage.setItem('history_context_rounds',v);fetch('/api/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({_config:true,key:'history_context_rounds',value:v})})" style="background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:6px 10px;color:var(--text);font-size:13px;font-family:var(--font);cursor:pointer;min-width:100px;">
          ${[2,4,8,16,32,64].map(v => `<option value="${v}" ${v === (parseInt(localStorage.getItem('history_context_rounds'))||8) ? 'selected' : ''}>${v} rounds</option>`).join('')}
        </select>
      </label>
    </div>

    <div class="settings-section-title">${_('Plan Mode Switch')}</div>
    <div class="settings-card" style="padding:16px;">
      <label style="display:flex;align-items:center;gap:12px;font-size:13px;">
        <span style="flex:1">
          <strong>${_('Default Decision')}</strong><br>
          <span style="color:var(--text-3);font-size:11.5px;">
            When the assistant requests to switch to Plan mode. "Deny" blocks all switches; "Allow" auto-approves; "Ask Every Time" shows a prompt.
          </span>
        </span>
        <select onchange="_setModeSwitchPolicy(this.value)" style="background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:6px 10px;color:var(--text);font-size:13px;font-family:var(--font);cursor:pointer;min-width:130px;">
          <option value="deny" ${(sbState.mode_switch_policy||'deny')==='deny'?'selected':''}>Deny</option>
          <option value="ask_always" ${(sbState.mode_switch_policy||'deny')==='ask_always'?'selected':''}>Ask Every Time</option>
          <option value="allow" ${(sbState.mode_switch_policy||'deny')==='allow'?'selected':''}>Allow</option>
        </select>
      </label>
    </div>
    <div class="settings-card" style="padding:16px;">
      <label style="display:flex;align-items:center;gap:12px;font-size:13px;">
        <span style="flex:1">
          <strong>${_('Switch Timeout')}</strong><br>
          <span style="color:var(--text-3);font-size:11.5px;">
            Time to wait for user decision before auto-denying the switch request.
          </span>
        </span>
        <div class="settings-stepper">
          <button class="stepper-btn down" onclick="_msTimeoutStep(-1)">&#x25BC;</button>
          <span class="stepper-value" id="ms-timeout-val">${sbState.mode_switch_timeout || 20}s</span>
          <button class="stepper-btn up" onclick="_msTimeoutStep(1)">&#x25B2;</button>
        </div>
      </label>
    </div>
  `;
}

function _calcEffectiveLabel(ratio) {
  const maxCtx = engine._rawMaxContextTokens || engine._maxContextTokens || 0;
  if (!maxCtx) return 'Effective limit: N/A';
  const eff = Math.round(maxCtx * ratio);
  return 'Effective limit: ' + (eff/1000).toFixed(1) + 'k tokens (' + (maxCtx/1000).toFixed(0) + 'k × ' + (ratio*100).toFixed(0) + '%)';
}

function _compressionStep(dir) {
  const cs = (window._sessionSettingsSchema || []).find(x => x.key === 'compression_ratio') || {};
  const defVal = cs.default || 0.5;
  const minPct = Math.round((cs.min || 0.25) * 100);
  const maxPct = Math.round((cs.max || 0.75) * 100);
  const stepPct = Math.round((cs.step || 0.05) * 100);
  const saved = parseFloat(localStorage.getItem('compression_ratio')) || defVal;
  let pct = Math.round(saved * 100) + dir * stepPct;
  pct = Math.max(minPct, Math.min(maxPct, pct));
  const ratio = pct / 100;
  localStorage.setItem('compression_ratio', String(ratio));
  document.getElementById('compression-ratio-val').textContent = pct + '%';
  const effEl = document.getElementById('compression-ratio-effective');
  if (effEl) effEl.textContent = _calcEffectiveLabel(ratio);
  fetch('/api/send', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({_config:true, key:'compression_ratio', value:ratio})});
  if (engine._rawMaxContextTokens) engine._maxContextTokens = Math.round(engine._rawMaxContextTokens * ratio);
}

function _getCtxLinesOptions() {
  const s = (window._sessionSettingsSchema || []).find(x => x.key === 'context_lines');
  return (s && s.options) || [0, 1, 2, 5, 10];
}
function _ctxLinesStep(dir) {
  const _CTX_LINES_OPTIONS = _getCtxLinesOptions();
  const defVal = ((window._sessionSettingsSchema || []).find(x => x.key === 'context_lines') || {}).default || 2;
  const cur = parseInt(localStorage.getItem('context_lines')) || defVal;
  let idx = _CTX_LINES_OPTIONS.indexOf(cur);
  if (idx < 0) idx = _CTX_LINES_OPTIONS.indexOf(defVal);
  idx = Math.max(0, Math.min(_CTX_LINES_OPTIONS.length - 1, idx + dir));
  const val = _CTX_LINES_OPTIONS[idx];
  localStorage.setItem('context_lines', String(val));
  document.getElementById('ctx-lines-val').textContent = val;
  fetch('/api/send', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({_config:true, key:'context_lines', value:val})});
}

function _blockLinesStep(key, dir) {
  const schema = (window._sessionSettingsSchema || []).find(x => x.key === key);
  const opts = (schema && schema.options) || (key === 'block_collapsed_lines' ? [4,5,6,8,10] : [12,14,16,18,20]);
  const defVal = (schema && schema.default) || (key === 'block_collapsed_lines' ? 6 : 16);
  const cur = parseInt(localStorage.getItem(key)) || defVal;
  let idx = opts.indexOf(cur);
  if (idx < 0) idx = opts.indexOf(defVal);
  idx = Math.max(0, Math.min(opts.length - 1, idx + dir));
  const val = opts[idx];
  localStorage.setItem(key, String(val));
  const valId = key === 'block_collapsed_lines' ? 'collapsed-lines-val' : 'expanded-lines-val';
  const valEl = document.getElementById(valId);
  if (valEl) valEl.textContent = val;
  fetch('/api/send', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({_config:true, key:key, value:val})});
  if (window.Collapsible) {
    window.Collapsible.configure({
      collapsed_lines: parseInt(localStorage.getItem('block_collapsed_lines')) || 6,
      expanded_lines: parseInt(localStorage.getItem('block_expanded_lines')) || 16,
    });
    window.Collapsible.refreshAll();
  }
}

function _setModeSwitchPolicy(val) {
  fetch('/api/sandbox/mode-switch-policy', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({policy: val})
  });
}

const _MS_TIMEOUT_STEPS = [5, 10, 20, 60, 180];
function _msTimeoutStep(dir) {
  const el = document.getElementById('ms-timeout-val');
  if (!el) return;
  const cur = parseInt(el.textContent);
  const idx = _MS_TIMEOUT_STEPS.indexOf(cur);
  const next = idx < 0 ? 20 : _MS_TIMEOUT_STEPS[Math.max(0, Math.min(_MS_TIMEOUT_STEPS.length-1, idx+dir))];
  el.textContent = next + 's';
  fetch('/api/sandbox/mode-switch-timeout', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({timeout: next})
  });
}

function renderModelsView() {
  const models = usageData.models || {};
  const calls = usageData.calls || [];
  const modelNames = Object.keys(models);
  if (!modelNames.length) {
    return `<div class="settings-section-title">${_('Models')}</div><div class="settings-empty">No model data yet. Start a conversation to see usage statistics.</div>`;
  }
  let html = `<div class="settings-section-title" style="display:flex;align-items:center;gap:10px;">${_('Models')}<input type="text" id="settings-model-search" placeholder="Filter..." oninput="renderSettingsTab()" style="margin-left:auto;width:120px;background:var(--bg);border:1px solid var(--border);border-radius:4px;padding:3px 8px;font-size:11px;color:var(--text);font-family:var(--font);outline:none;"></div>`;
  const modelSearch = (document.getElementById('settings-model-search')?.value || '').toLowerCase();
  for (const name of modelNames) {
    const m = models[name];
    if (modelSearch && !(MODEL_DISPLAY_NAMES[name] || name).toLowerCase().includes(modelSearch)) continue;
    const logo = MODEL_LOGOS[name] || resolveModelLogo(name) || '';
    const displayName = MODEL_DISPLAY_NAMES[name] || name;
    const configuredProvs = new Set(m.configured_providers || []);
    const provChips = (m.providers || []).map(p => {
      const isProvConfigured = configuredProvs.has(p);
      const chipStyle = isProvConfigured ? 'background:var(--configured-bg);color:var(--configured-text);' : '';
      const vendor = p.split('-')[0];
      return `<div class="settings-provider-chip" onclick="switchSettingsTab('providers');setTimeout(()=>{const c=document.querySelector('[data-provider-id=\\'${esc(vendor)}\\']');if(c)c.scrollIntoView({behavior:'smooth',block:'center'})},100)" style="cursor:pointer;${chipStyle}">${PROVIDER_LOGOS[vendor] ? '<img src="' + PROVIDER_LOGOS[vendor] + '" style="width:12px;height:12px;border-radius:2px;vertical-align:middle;margin-right:2px;">' : ''} ${esc(fmtProviderName(vendor))}${fmtProviderPriceInner(m)}</div>`;
    }).join('');
    const modelCalls = calls.filter(c => c.model === name || c.provider === name);
    const aa = m.aa_benchmarks || {};
    const aaRank = m.aa_rankings || {};
    let benchTags = '';
    const _rankColor = (r) => {
      if (!r) return 'var(--badge-bg);color:var(--badge-text)';
      if (r <= 3) return r === 1 ? 'var(--bench-gold);color:#000;background-size:200% 200%;animation:shimmer 2s ease infinite' : r === 2 ? 'var(--bench-silver);color:#333;background-size:200% 200%;animation:shimmer 2s ease infinite' : 'var(--bench-bronze);color:#fff;background-size:200% 200%;animation:shimmer 2s ease infinite';
      if (r <= 5) return 'var(--purple-dim);color:var(--purple)';
      if (r <= 10) return 'var(--accent-dim);color:var(--accent)';
      if (r <= 20) return 'var(--configured-bg);color:var(--configured-text)';
      return 'var(--badge-bg);color:var(--badge-text)';
    };
    const _benchTag = (label, val, rank, benchKey) => {
      if (!val) return '';
      const rStr = rank ? ` (#${rank})` : '';
      const fVal = typeof val === 'number' ? (val >= 10 ? val.toFixed(1) : val.toFixed(3)) : val;
      return `<span class="settings-badge" style="background:${_rankColor(rank)};margin-left:2px;cursor:pointer;" onclick="openBenchOverlay('${esc(name)}',event)" title="${BENCH_LABELS[benchKey] || benchKey}: ${fVal}">${BENCH_SHORT[benchKey] || benchKey} ${fVal}${rStr}</span>`;
    };
    const rankedBenches = Object.entries(aaRank)
      .filter(([k]) => !k.startsWith('_') && aa[k] != null)
      .sort((a, b) => a[1] - b[1]);
    const MAX_CHIPS = 3;
    for (let i = 0; i < Math.min(MAX_CHIPS, rankedBenches.length); i++) {
      const [benchKey, rank] = rankedBenches[i];
      benchTags += _benchTag(BENCH_SHORT[benchKey] || benchKey, aa[benchKey], rank, benchKey);
    }
    if (rankedBenches.length > MAX_CHIPS) {
      benchTags += `<span class="settings-badge" style="background:var(--surface-3);color:var(--text-2);margin-left:2px;cursor:pointer;font-size:9px;" onclick="openBenchOverlay('${esc(name)}',event)" title="Show all ${rankedBenches.length} benchmarks">+${rankedBenches.length - MAX_CHIPS}</span>`;
    }
    const isConfigured = m.configured;
    const isLocked = m.active === false;
    const lockReason = m.lock_reason || '';
    const cardClass = isLocked ? 'settings-card locked' : (isConfigured ? 'settings-card configured' : 'settings-card unconfigured');
    const lockBadge = isLocked ? `<span class="settings-badge" style="background:var(--surface-3);color:var(--text-3);margin-left:auto;font-size:10px;flex-shrink:0;"><i class="bx bx-lock-alt" style="font-size:10px;vertical-align:middle;"></i> ${_('Locked')}</span>` : '';
    const configBadge = !isLocked && isConfigured ? '<span class="settings-badge" style="background:var(--configured-bg);color:var(--configured-text);margin-left:auto;font-size:10px;flex-shrink:0;">' + _('Configured') + '</span>' : '';
    const lockNotice = isLocked && lockReason ? `<div style="margin-top:8px;padding:6px 10px;background:var(--surface-2);border-radius:6px;font-size:11px;color:var(--text-3);"><i class="bx bx-info-circle" style="vertical-align:middle;margin-right:4px;"></i>${esc(lockReason)}</div>` : '';
    html += `<div class="${cardClass}"${isLocked ? ' style="opacity:0.6;pointer-events:none;position:relative;"' : ''}>
      ${isLocked ? '<div style="position:absolute;inset:0;z-index:2;cursor:not-allowed;pointer-events:auto;" title="' + esc(lockReason || 'Model is locked') + '"></div>' : ''}
      <div class="settings-card-title">${logo ? '<img src="' + logo + '" alt="">' : '<i class="bx bx-bot" style="font-size:16px;color:var(--accent)"></i>'}<span class="model-name-text" title="${esc(displayName)}">${esc(displayName)}</span>${benchTags}${lockBadge}${configBadge}</div>
      ${lockNotice}
      <div class="settings-stats">
        <div class="settings-stat"><div class="settings-stat-value">${m.total_calls || 0}</div><div class="settings-stat-label">Calls</div></div>
        <div class="settings-stat"><div class="settings-stat-value">${fmtTokens(m.input_tokens || 0)}</div><div class="settings-stat-label">Input<br>Tokens</div></div>
        <div class="settings-stat"><div class="settings-stat-value">${fmtTokens(m.output_tokens || 0)}</div><div class="settings-stat-label">Output<br>Tokens</div></div>
        <div class="settings-stat"><div class="settings-stat-value">${m.total_cost ? _priceStr(m.total_cost) : _priceStr(0)}</div><div class="settings-stat-label">Cost</div></div>
      </div>
      ${isLocked ? '' : _renderModelCaps(name, m)}
      ${provChips ? '<div style="margin-top:16px;font-size:11px;color:var(--text-3);font-weight:600;text-transform:uppercase;letter-spacing:0.3px;margin-bottom:6px;">Providers</div><div class="settings-provider-list">' + provChips + '</div>' : ''}
      ${isLocked ? '' : renderCallsTable(modelCalls, 'model_' + name)}
    </div>`;
  }
  return html;
}

function _floorPow2(n) {
  if (n <= 0) return 1;
  let p = 1;
  while (p * 2 <= n) p *= 2;
  return p;
}
function _renderModelCaps(modelId, m) {
  const cap = m.capabilities || {};
  const ctx = cap.max_context_tokens || 0;
  const maxOut = cap.max_output_tokens || 0;
  if (!ctx && !maxOut) return '';
  const fK = (n) => n >= 1048576 ? Math.floor(n/1048576)+'m' : n >= 1024 ? Math.floor(n/1024)+'k' : String(Math.floor(n));
  const ctxBase = _floorPow2(ctx);
  const inputDefault = ctxBase / 16 || 4096;
  const inputMax = ctxBase / 4 || 65536;
  const outputDefault = ctxBase / 8 || 2048;
  const outputMax = ctxBase / 2 || 32768;
  let savedIn = parseInt(localStorage.getItem('model_input_' + modelId)) || inputDefault;
  let savedOut = parseInt(localStorage.getItem('model_output_' + modelId)) || outputDefault;
  savedIn = _floorPow2(Math.min(Math.max(savedIn, 1024), inputMax));
  savedOut = _floorPow2(Math.min(Math.max(savedOut, 256), outputMax));
  const features = [];
  if (cap.tool_calling) features.push('<i class="bx bx-wrench"></i> Tools');
  if (cap.vision) features.push('<i class="bx bx-show"></i> Vision');
  if (cap.streaming) features.push('<i class="bx bx-transfer"></i> Stream');
  if (cap.reasoning) features.push('<i class="bx bx-brain"></i> Reason');
  const featureTags = features.map(f => `<span style="font-size:10px;padding:2px 8px;border-radius:10px;background:var(--surface-3);color:var(--text-2);display:inline-flex;align-items:center;gap:3px;">${f}</span>`).join(' ');
  const specItems = [];
  if (ctx) specItems.push(`<div style="text-align:center;"><div style="font-size:14px;font-weight:700;color:var(--text);font-family:var(--mono);">${fK(ctx)}</div><div style="font-size:9px;color:var(--text-3);text-transform:uppercase;letter-spacing:0.3px;margin-top:1px;">Context</div></div>`);
  if (maxOut) specItems.push(`<div style="text-align:center;"><div style="font-size:14px;font-weight:700;color:var(--text);font-family:var(--mono);">${fK(maxOut)}</div><div style="font-size:9px;color:var(--text-3);text-transform:uppercase;letter-spacing:0.3px;margin-top:1px;">Max Output</div></div>`);
  return `<div style="margin-top:16px;font-size:11px;color:var(--text-3);font-weight:600;text-transform:uppercase;letter-spacing:0.3px;margin-bottom:8px;">Capabilities</div>
    <div style="display:flex;align-items:center;gap:20px;margin-bottom:10px;padding:8px 12px;background:var(--bg);border-radius:8px;border:1px solid var(--border);">
      ${specItems.join('<div style="width:1px;height:24px;background:var(--border);"></div>')}
      <div style="margin-left:auto;display:flex;flex-wrap:wrap;gap:4px;">${featureTags}</div>
    </div>
    <div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap;font-size:12px;">
      <label style="display:flex;align-items:center;gap:6px;">
        <span style="color:var(--text-2);font-size:11px;">Input Limit</span>
        <div class="settings-stepper" data-key="model_input_${modelId}" data-min="1024" data-max="${inputMax}" data-default="${inputDefault}" data-mode="pow2">
          <button class="stepper-btn down" onclick="_stepperClick(this,-1)">\u25BC</button>
          <span class="stepper-value">${fK(savedIn)}</span>
          <button class="stepper-btn up" onclick="_stepperClick(this,1)">\u25B2</button>
        </div>
      </label>
      <label style="display:flex;align-items:center;gap:6px;">
        <span style="color:var(--text-2);font-size:11px;">Output Limit</span>
        <div class="settings-stepper" data-key="model_output_${modelId}" data-min="256" data-max="${outputMax}" data-default="${outputDefault}" data-mode="pow2">
          <button class="stepper-btn down" onclick="_stepperClick(this,-1)">\u25BC</button>
          <span class="stepper-value">${fK(savedOut)}</span>
          <button class="stepper-btn up" onclick="_stepperClick(this,1)">\u25B2</button>
        </div>
      </label>
    </div>`;
}

let _dataSessionId = '';
let _dataCache = null;

function _fmtBytes(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(2) + ' MB';
}

async function renderDataView() {
  const sessions = window._allSessions || [];
  if (!_dataSessionId && sessions.length) {
    _dataSessionId = sessions[0].id || '';
  }

  const sessionOpts = sessions.map(s =>
    `<option value="${s.id}" ${s.id === _dataSessionId ? 'selected' : ''}>${esc(s.title || s.id)} (${s.id.slice(0,8)})</option>`
  ).join('');

  let dataHtml = '';
  if (_dataSessionId) {
    try {
      const resp = await fetch(`/api/session/${_dataSessionId}/data`);
      const data = await resp.json();
      if (data.ok) {
        _dataCache = data;
        const types = data.types || {};
        const protectedRounds = data.protected_rounds || 8;
        const TYPE_LABELS = { input: 'Input', output: 'Output', context: 'Context', read: 'Read', edit: 'Edit', exec: 'Exec' };
        const TYPE_ICONS = { input: 'bx-log-in', output: 'bx-log-out', context: 'bx-conversation', read: 'bx-file', edit: 'bx-edit', exec: 'bx-terminal' };

        for (const [dtype, info] of Object.entries(types)) {
          const label = TYPE_LABELS[dtype] || dtype;
          const icon = TYPE_ICONS[dtype] || 'bx-data';
          const maxPurge = Math.max(0, info.count - (dtype === 'rounds' ? protectedRounds : 0));
          dataHtml += `
            <div class="data-type-row">
              <span class="data-type-label"><i class="bx ${icon}" style="font-size:14px;vertical-align:middle;margin-right:4px;"></i> ${label}</span>
              <span class="data-type-count">${info.count} items</span>
              <span class="data-type-mem">${_fmtBytes(info.memory_bytes)}</span>
              ${maxPurge > 0 ? `<button class="data-purge-btn" onclick="_togglePurgePanel('${dtype}')">Clean</button>` : `<span style="font-size:11px;color:var(--text-3);min-width:50px;text-align:center;">—</span>`}
            </div>
            <div class="data-slider-panel" id="purge-panel-${dtype}">
              <div class="data-slider-wrap">
                <label>
                  <span>By count:</span>
                  <span id="purge-count-val-${dtype}">0 / ${maxPurge}</span>
                </label>
                <input type="range" class="data-slider" min="0" max="${maxPurge}" value="0"
                  oninput="_onPurgeCountSlide('${dtype}', this.value, ${maxPurge}, ${info.memory_bytes}, ${info.count})" />
              </div>
              <div class="data-slider-wrap">
                <label>
                  <span>By memory:</span>
                  <span id="purge-mem-val-${dtype}">0 B / ${_fmtBytes(info.memory_bytes)}</span>
                </label>
                <input type="range" class="data-slider" min="0" max="${info.memory_bytes}" value="0" step="1024"
                  oninput="_onPurgeMemSlide('${dtype}', this.value, ${maxPurge}, ${info.memory_bytes}, ${info.count})" />
              </div>
              <div style="display:flex;gap:8px;margin-top:8px;">
                <button class="data-purge-btn" style="color:var(--red);border-color:var(--red);" onclick="_executePurge('${dtype}')">Purge selected</button>
                <button class="data-purge-btn" onclick="_togglePurgePanel('${dtype}')">Cancel</button>
              </div>
            </div>`;
        }

        dataHtml += `
          <div class="data-type-row" style="margin-top:8px;border-top:2px solid var(--border);padding-top:12px;">
            <span class="data-type-label"><i class="bx bx-layer" style="font-size:14px;vertical-align:middle;margin-right:4px;"></i> <strong>Rounds</strong></span>
            <span class="data-type-count">${data.total_rounds} total</span>
            <span class="data-type-mem">${_fmtBytes(data.events_memory_bytes)}</span>
            ${data.total_rounds > protectedRounds ? `<button class="data-purge-btn" onclick="_togglePurgePanel('rounds')">Clean</button>` : `<span style="font-size:11px;color:var(--text-3);min-width:50px;text-align:center;">—</span>`}
          </div>
          <div class="data-slider-panel" id="purge-panel-rounds">
            <div class="data-slider-wrap">
              <label>
                <span>Purge oldest rounds (${protectedRounds} protected):</span>
                <span id="purge-count-val-rounds">0 / ${Math.max(0, data.total_rounds - protectedRounds)}</span>
              </label>
              <input type="range" class="data-slider" min="0" max="${Math.max(0, data.total_rounds - protectedRounds)}" value="0"
                oninput="document.getElementById('purge-count-val-rounds').textContent = this.value + ' / ${Math.max(0, data.total_rounds - protectedRounds)}'" />
            </div>
            <div style="display:flex;gap:8px;margin-top:8px;">
              <button class="data-purge-btn" style="color:var(--red);border-color:var(--red);" onclick="_executePurge('rounds')">Purge selected</button>
              <button class="data-purge-btn" onclick="_togglePurgePanel('rounds')">Cancel</button>
            </div>
          </div>
          <div style="font-size:11px;color:var(--text-3);margin-top:12px;">
            Protected rounds: last ${protectedRounds} (configurable in Chat settings as "History Context Rounds")
          </div>`;
      } else {
        dataHtml = `<div style="color:var(--text-3);font-size:12px;">${data.error || 'Failed to load data'}</div>`;
      }
    } catch (e) {
      dataHtml = `<div style="color:var(--text-3);font-size:12px;">Error loading data: ${e.message}</div>`;
    }
  }

  return `
    <div class="settings-section-title">${_('Session Data')}</div>
    <div class="settings-card" style="padding:16px;">
      <label style="display:flex;align-items:center;gap:12px;font-size:13px;margin-bottom:14px;">
        <span style="flex:1;font-weight:600;">Session</span>
        <select onchange="_dataSessionId=this.value;renderSettingsTab();" style="background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:6px 10px;color:var(--text);font-size:13px;font-family:var(--font);cursor:pointer;min-width:220px;max-width:340px;">
          ${sessionOpts}
        </select>
      </label>
      ${dataHtml}
    </div>`;
}

function _togglePurgePanel(dtype) {
  const el = document.getElementById('purge-panel-' + dtype);
  if (el) el.classList.toggle('open');
}

function _onPurgeCountSlide(dtype, val, maxPurge, totalMem, totalCount) {
  val = parseInt(val);
  document.getElementById('purge-count-val-' + dtype).textContent = val + ' / ' + maxPurge;
  const estMem = totalCount > 0 ? Math.round(totalMem * val / totalCount) : 0;
  document.getElementById('purge-mem-val-' + dtype).textContent = _fmtBytes(estMem) + ' / ' + _fmtBytes(totalMem);
  const memSlider = document.querySelector('#purge-panel-' + dtype + ' input[type=range]:last-of-type');
  if (memSlider) memSlider.value = estMem;
}

function _onPurgeMemSlide(dtype, val, maxPurge, totalMem, totalCount) {
  val = parseInt(val);
  const estCount = totalMem > 0 ? Math.min(maxPurge, Math.ceil(totalCount * val / totalMem)) : 0;
  document.getElementById('purge-mem-val-' + dtype).textContent = _fmtBytes(val) + ' / ' + _fmtBytes(totalMem);
  document.getElementById('purge-count-val-' + dtype).textContent = estCount + ' / ' + maxPurge;
  const countSlider = document.querySelector('#purge-panel-' + dtype + ' input[type=range]:first-of-type');
  if (countSlider) countSlider.value = estCount;
}

async function _executePurge(dtype) {
  const countSlider = document.querySelector('#purge-panel-' + dtype + ' input[type=range]:first-of-type');
  const count = countSlider ? parseInt(countSlider.value) : 0;
  if (count <= 0) return;
  try {
    const resp = await fetch(`/api/session/${_dataSessionId}/purge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: dtype, count }),
    });
    const data = await resp.json();
    if (data.ok) {
      renderSettingsTab();
    } else {
      alert(data.error || 'Purge failed');
    }
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

async function renderBrainView() {
  let blueprintsHtml = '', instancesHtml = '', activeHtml = '';
  try {
    const [bpRes, instRes, actRes] = await Promise.all([
      fetch('/api/brain/blueprints').then(r => r.json()),
      fetch('/api/brain/instances').then(r => r.json()),
      fetch('/api/brain/active').then(r => r.json()),
    ]);
    const activeName = actRes.ok ? (actRes.active || 'default') : 'default';
    activeHtml = `<div style="font-size:13px;color:var(--text-2);margin-bottom:16px;">Active session: <strong style="color:var(--text)">${esc(activeName)}</strong></div>`;

    if (bpRes.ok && bpRes.blueprints) {
      blueprintsHtml = bpRes.blueprints.map(bp => {
        const name = bp.name || bp;
        const desc = bp.description || '';
        const ver = bp.version || '';
        return `<div class="settings-card" style="padding:12px 16px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <i class="bx bx-file" style="font-size:18px;color:var(--purple)"></i>
            <strong style="font-size:13px;">${esc(name)}</strong>
            ${ver ? `<span style="font-size:10px;color:var(--text-3);">v${esc(ver)}</span>` : ''}
          </div>
          ${desc ? `<div style="font-size:11.5px;color:var(--text-3);margin-top:4px;line-height:1.4;">${esc(desc)}</div>` : ''}
        </div>`;
      }).join('');
    }

    if (instRes.ok && instRes.instances) {
      if (instRes.instances.length === 0) {
        instancesHtml = '<div style="font-size:12px;color:var(--text-3);padding:8px 0;">No sessions created yet.</div>';
      } else {
        instancesHtml = instRes.instances.map(inst => {
          const name = inst.name || '?';
          const isActive = inst.active;
          const tasks = inst.tasks != null ? inst.tasks : '?';
          const activity = inst.activity_entries || 0;
          const updated = inst.updated || '';
          return `<div class="settings-card${isActive ? ' configured' : ''}" style="padding:12px 16px;">
            <div style="display:flex;align-items:center;gap:8px;">
              <i class="bx ${isActive ? 'bx-check-circle' : 'bx-circle'}" style="font-size:16px;color:${isActive ? 'var(--green)' : 'var(--text-3)'}"></i>
              <strong style="font-size:13px;">${esc(name)}</strong>
              ${isActive ? '<span class="settings-badge" style="background:var(--green-card-bg);color:var(--green)">active</span>' : `<button style="margin-left:auto;font-size:11px;padding:3px 10px;border:1px solid var(--border);border-radius:4px;background:var(--bg);color:var(--text-2);cursor:pointer;" onclick="_brainSwitch('${esc(name)}')">Switch</button>`}
            </div>
            <div style="display:flex;gap:12px;font-size:11px;color:var(--text-3);margin-top:6px;">
              <span><i class="bx bx-task"></i> ${tasks} tasks</span>
              <span><i class="bx bx-pulse"></i> ${activity} log entries</span>
              ${updated ? `<span><i class="bx bx-time-five"></i> ${esc(updated)}</span>` : ''}
            </div>
          </div>`;
        }).join('');
      }
    }
  } catch (e) {
    console.warn('Brain fetch error:', e);
  }

  return `
    <div class="settings-section-title"><i class="bx bx-brain"></i> ${_('Brain')}</div>
    ${activeHtml}
    <div style="font-size:14px;font-weight:600;margin-bottom:8px;color:var(--text);">Sessions</div>
    ${instancesHtml || '<div style="font-size:12px;color:var(--text-3)">No brain data available.</div>'}
    <div style="margin-top:20px;font-size:14px;font-weight:600;margin-bottom:8px;color:var(--text);">Available Blueprints</div>
    ${blueprintsHtml || '<div style="font-size:12px;color:var(--text-3)">No blueprints found.</div>'}
  `;
}
async function _brainSwitch(name) {
  try {
    const res = await fetch('/api/brain/switch', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name}) });
    const data = await res.json();
    if (data.ok) renderSettingsTab();
    else alert(data.error || 'Switch failed');
  } catch (e) { alert('Switch failed: ' + e.message); }
}

let _sbCmdPage = 0;
const _SB_PAGE_SIZE = 8;

async function renderPermissionsView() {
  try {
    const res = await fetch('/api/sandbox/state');
    const data = await res.json();
    if (!data.ok) return `<div class="settings-section-title">Permissions</div><div class="settings-empty">Failed to load: ${data.error}</div>`;
    const sp = data.system_policy || 'ask_always';
    const perms = data.command_permissions || {};
    const permKeys = Object.keys(perms).sort();
    const popupTimeout = data.popup_timeout || 20;

    let html = `<div class="settings-section-title">Permissions</div>`;

    html += `<div class="settings-card">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
        <span style="font-size:13px;font-weight:600;">System Policy</span>
        <select onchange="_sbSetSystemPolicy(this.value)" style="margin-left:auto;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:5px 10px;color:var(--text);font-size:12px;font-family:var(--font);cursor:pointer;">
          <option value="ask_always"${sp==='ask_always'?' selected':''}>Ask every time</option>
          <option value="run_all"${sp==='run_all'?' selected':''}>Run everything</option>
        </select>
      </div>
      <div style="color:var(--text-3);font-size:11.5px;">Global execution policy for all commands. When set to "Ask", new commands require approval before running.</div>
    </div>`;

    const bp = data.boundary_policy || 'ask_always';
    html += `<div class="settings-card" style="margin-top:10px;">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
        <span style="font-size:13px;font-weight:600;">Workspace Boundary</span>
        <select onchange="_sbSetBoundaryPolicy(this.value)" style="margin-left:auto;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:5px 10px;color:var(--text);font-size:12px;font-family:var(--font);cursor:pointer;">
          <option value="ask_always"${bp==='ask_always'?' selected':''}>Ask every time</option>
          <option value="allow_all"${bp==='allow_all'?' selected':''}>Allow all</option>
          <option value="deny_all"${bp==='deny_all'?' selected':''}>Deny all</option>
        </select>
      </div>
      <div style="color:var(--text-3);font-size:11.5px;">Policy for exec/edit operations outside the workspace boundary. "Ask every time" requires one-time approval (never persisted).</div>
    </div>`;

    html += `<div class="settings-card" style="margin-top:10px;">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
        <span style="font-size:13px;font-weight:600;">Popup Timeout</span>
        <div style="margin-left:auto;display:flex;align-items:center;gap:4px;">
          <button onclick="_sbAdjustTimeout(-1)" style="border:1px solid var(--border);background:var(--bg);color:var(--text);width:24px;height:24px;border-radius:4px;cursor:pointer;font-size:14px;display:flex;align-items:center;justify-content:center;">&minus;</button>
          <span id="sb-timeout-val" style="font-family:var(--mono);font-size:13px;min-width:36px;text-align:center;">${popupTimeout}s</span>
          <button onclick="_sbAdjustTimeout(1)" style="border:1px solid var(--border);background:var(--bg);color:var(--text);width:24px;height:24px;border-radius:4px;cursor:pointer;font-size:14px;display:flex;align-items:center;justify-content:center;">+</button>
        </div>
      </div>
      <div style="color:var(--text-3);font-size:11.5px;">How long the approval popup waits before auto-denying. Mandatory approvals (workspace boundary) have no timeout.</div>
    </div>`;

    html += `<div class="settings-section-title">Command Policy</div>`;
    if (permKeys.length === 0) {
      html += `<div style="color:var(--text-3);font-size:12px;padding:8px 0;">No command policies set. Policies are created when new commands are encountered.</div>`;
    } else {
      const totalPages = Math.ceil(permKeys.length / _SB_PAGE_SIZE);
      if (_sbCmdPage >= totalPages) _sbCmdPage = totalPages - 1;
      if (_sbCmdPage < 0) _sbCmdPage = 0;
      const pageKeys = permKeys.slice(_sbCmdPage * _SB_PAGE_SIZE, (_sbCmdPage + 1) * _SB_PAGE_SIZE);
      html += `<table class="settings-table"><tbody>`;
      for (const cmd of pageKeys) {
        const pol = perms[cmd];
        const polColor = pol === 'always' ? 'var(--green)' : pol === 'forbidden' ? 'var(--red)' : 'var(--text-2)';
        html += `<tr><td style="font-family:var(--mono);font-size:12px;">${cmd}</td>
          <td><select onchange="_sbSetCmdPerm('${cmd}',this.value)" style="background:var(--bg);border:1px solid var(--border);border-radius:4px;padding:2px 6px;color:${polColor};font-size:11px;font-family:var(--mono);cursor:pointer;">
            <option value="always"${pol==='always'?' selected':''}>Always allow</option>
            <option value="once"${pol==='once'?' selected':''}>Once</option>
            <option value="forbidden"${pol==='forbidden'?' selected':''}>Forbidden</option>
          </select></td>
          <td><button onclick="_sbRemoveCmdPerm('${cmd}')" style="border:none;background:none;color:var(--text-3);cursor:pointer;font-size:14px;" title="Remove"><i class='bx bx-trash'></i></button></td></tr>`;
      }
      html += `</tbody></table>`;
      if (totalPages > 1) {
        html += `<div style="display:flex;align-items:center;justify-content:center;gap:12px;margin-top:8px;">
          <button onclick="_sbCmdPageNav(-1)" style="border:1px solid var(--border);background:var(--bg);color:var(--text-3);width:28px;height:28px;border-radius:4px;cursor:pointer;font-size:14px;display:flex;align-items:center;justify-content:center;"${_sbCmdPage===0?' disabled style="opacity:0.3;pointer-events:none;border:1px solid var(--border);background:var(--bg);color:var(--text-3);width:28px;height:28px;border-radius:4px;cursor:pointer;font-size:14px;display:flex;align-items:center;justify-content:center;"':''}><i class='bx bx-chevron-left'></i></button>
          <span style="font-size:11px;color:var(--text-3);">${_sbCmdPage+1} / ${totalPages}</span>
          <button onclick="_sbCmdPageNav(1)" style="border:1px solid var(--border);background:var(--bg);color:var(--text-3);width:28px;height:28px;border-radius:4px;cursor:pointer;font-size:14px;display:flex;align-items:center;justify-content:center;"${_sbCmdPage>=totalPages-1?' disabled style="opacity:0.3;pointer-events:none;border:1px solid var(--border);background:var(--bg);color:var(--text-3);width:28px;height:28px;border-radius:4px;cursor:pointer;font-size:14px;display:flex;align-items:center;justify-content:center;"':''}><i class='bx bx-chevron-right'></i></button>
        </div>`;
      }
    }
    return html;
  } catch(e) {
    return `<div class="settings-section-title">Permissions</div><div class="settings-empty">Error: ${e.message}</div>`;
  }
}

function _sbSetSystemPolicy(val) {
  fetch('/api/sandbox/system-policy', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({policy:val}) });
}
function _sbSetCmdPerm(cmd, pol) {
  fetch('/api/sandbox/command', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({command:cmd, policy:pol}) }).then(()=>renderSettingsTab());
}
function _sbRemoveCmdPerm(cmd) {
  fetch('/api/sandbox/command', { method:'DELETE', headers:{'Content-Type':'application/json'}, body: JSON.stringify({command:cmd}) }).then(()=>renderSettingsTab());
}
function _sbSetBoundaryPolicy(val) {
  fetch('/api/sandbox/boundary-policy', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({policy:val}) });
}
const _SB_TIMEOUT_STEPS = [5, 10, 20, 60, 180];
function _sbAdjustTimeout(dir) {
  const el = document.getElementById('sb-timeout-val');
  if (!el) return;
  const cur = parseInt(el.textContent);
  const idx = _SB_TIMEOUT_STEPS.indexOf(cur);
  const next = idx < 0 ? 20 : _SB_TIMEOUT_STEPS[Math.max(0, Math.min(_SB_TIMEOUT_STEPS.length-1, idx+dir))];
  el.textContent = next + 's';
  fetch('/api/sandbox/timeout', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({timeout:next}) });
}
function _sbCmdPageNav(dir) {
  _sbCmdPage += dir;
  renderSettingsTab();
}

function renderProvidersView() {
  const providers = usageData.providers || {};
  const calls = usageData.calls || [];
  const provNames = Object.keys(providers);
  if (!provNames.length) {
    return `<div class="settings-section-title">${_('Providers')}</div><div class="settings-empty">No provider data yet. Start a conversation to see usage statistics.</div>`;
  }
  let html = `<div class="settings-section-title" style="display:flex;align-items:center;gap:10px;">${_('Providers')}<input type="text" id="settings-prov-search" placeholder="Filter..." oninput="renderSettingsTab()" style="margin-left:auto;width:120px;background:var(--bg);border:1px solid var(--border);border-radius:4px;padding:3px 8px;font-size:11px;color:var(--text);font-family:var(--font);outline:none;"></div>`;
  const provSearch = (document.getElementById('settings-prov-search')?.value || '').toLowerCase();
  for (const name of provNames) {
    const p = providers[name];
    if (provSearch && !name.toLowerCase().includes(provSearch)) continue;
    const displayName = fmtProviderName(name);
    const modelChips = (p.models || []).map(m => {
      const mData = (usageData.models || {})[m];
      const badge = mData ? ' ' + fmtPriceBadge(mData) : '';
      const mLogo = MODEL_LOGOS[m] ? '<img src="' + MODEL_LOGOS[m] + '" style="width:12px;height:12px;border-radius:2px;vertical-align:middle;margin-right:2px;">' : '';
      return `<div class="settings-provider-chip">${mLogo}${esc(MODEL_DISPLAY_NAMES[m] || m)}${badge}</div>`;
    }).join('');
    const keysHtml = (p.api_keys || []).map(k => {
      const isStale = k.state === 'stale';
      const staleTag = isStale
        ? `<span style="font-size:10px;padding:1px 6px;background:var(--red-dim);color:var(--red);border-radius:3px;font-weight:600;" title="${esc(k.state_reason || 'Key is stale')}">stale</span>
           <button onclick="reverifyKey('${esc(name)}','${esc(k.id)}',this)" style="font-size:10px;padding:1px 6px;background:var(--accent-dim);color:var(--accent);border:none;border-radius:3px;cursor:pointer;font-weight:600;" title="Re-verify this key"><i class='bx bx-refresh' style='font-size:11px;vertical-align:middle;'></i> Verify</button>`
        : '';
      return `<div class="settings-key-row"><span class="settings-key-mask">${maskKey(k.key)}</span><span class="settings-key-label">${esc(k.label || 'default')}</span>${staleTag}<button class="settings-key-delete" title="Delete key" onclick="deleteApiKey('${esc(name)}',this)"><i class="bx bx-trash"></i></button></div>`;
    }).join('') || '<div style="font-size:11px;color:var(--text-3);padding:4px 0;">No API keys configured</div>';
    const provCalls = calls.filter(c => (c.provider || '').includes(name));
    const provConfigured = p.configured;
    const provCardClass = provConfigured ? 'settings-card configured' : 'settings-card unconfigured';
    html += `<div class="${provCardClass}" data-provider-id="${esc(name)}">
      <div class="settings-card-title">${PROVIDER_LOGOS[name] ? '<img src="' + PROVIDER_LOGOS[name] + '" alt="" style="width:16px;height:16px;border-radius:3px;">' : '<i class="bx bx-server" style="font-size:16px;color:var(--accent)"></i>'} ${esc(displayName)}${provConfigured ? '<span class="settings-badge" style="background:var(--configured-bg);color:var(--configured-text);margin-left:auto;font-size:10px;">' + _('Configured') + '</span>' : ''}</div>
      <div class="settings-stats">
        <div class="settings-stat"><div class="settings-stat-value">${p.total_calls || 0}</div><div class="settings-stat-label">Calls</div></div>
        <div class="settings-stat"><div class="settings-stat-value">${fmtTokens(p.input_tokens || 0)}</div><div class="settings-stat-label">Input<br>Tokens</div></div>
        <div class="settings-stat"><div class="settings-stat-value">${fmtTokens(p.output_tokens || 0)}</div><div class="settings-stat-label">Output<br>Tokens</div></div>
        <div class="settings-stat"><div class="settings-stat-value">${p.total_cost ? _priceStr(p.total_cost) : _priceStr(0)}</div><div class="settings-stat-label">Cost</div></div>
      </div>
      ${modelChips ? '<div style="margin-top:8px;font-size:11px;color:var(--text-3);font-weight:600;text-transform:uppercase;letter-spacing:0.3px;margin-bottom:4px;">Models</div><div class="settings-provider-list">' + modelChips + '</div>' : ''}
      <div style="margin-top:10px;display:flex;align-items:center;gap:8px;margin-bottom:4px;">
        <span style="font-size:11px;color:var(--text-3);font-weight:600;text-transform:uppercase;letter-spacing:0.3px;">API Keys</span>
        <button class="settings-add-key-btn" onclick="toggleKeyInput(this.closest('.settings-card').querySelector('.settings-key-form'))" style="margin-left:auto;font-size:10px;padding:2px 8px;background:var(--accent-dim);color:var(--accent);border:none;border-radius:4px;cursor:pointer;font-weight:600;"><i class="bx bx-plus" style="font-size:11px;vertical-align:middle;"></i> Add Key</button>
        <button onclick="showProviderGuide('${esc(name)}')" style="font-size:10px;padding:2px 8px;background:var(--surface-3);color:var(--text-2);border:none;border-radius:4px;cursor:pointer;font-weight:600;"><i class="bx bx-book-open" style="font-size:11px;vertical-align:middle;"></i> ${_('Guide')}</button>
      </div>
      ${keysHtml}
      <div class="settings-add-key" data-vendor="${esc(name)}">
        <div class="settings-key-form" style="display:none;">
          <div class="settings-key-form-row">
            <input type="password" placeholder="Paste API key..." class="settings-key-input">
            <button class="settings-validate-btn" onclick="validateAndSaveKey(this)">${_('Validate & Save')}</button>
          </div>
          <div class="settings-key-status"></div>
        </div>
      </div>
      ${renderCallsTable(provCalls, 'prov_' + name)}
    </div>`;
  }
  return html;
}

const CALLS_PER_PAGE = 8;
const MAX_STORED_CALLS = 1024;
const _callsPageState = {};

function renderCallsTable(calls, tableId) {
  if (!calls.length) return '';
  const all = calls.slice(-MAX_STORED_CALLS).reverse();
  const totalPages = Math.max(1, Math.ceil(all.length / CALLS_PER_PAGE));
  if (!_callsPageState[tableId]) _callsPageState[tableId] = 1;
  const page = Math.min(_callsPageState[tableId], totalPages);
  const start = (page - 1) * CALLS_PER_PAGE;
  const pageItems = all.slice(start, start + CALLS_PER_PAGE);

  const pagerHtml = totalPages > 1 ? `<div style="display:flex;align-items:center;justify-content:center;gap:8px;margin-top:6px;font-size:11px;color:var(--text-3);">
    <button onclick="_callsPageNav('${tableId}',-1)" style="background:none;border:1px solid var(--border);border-radius:4px;color:var(--text-2);cursor:pointer;padding:2px 8px;font-size:11px;" ${page <= 1 ? 'disabled' : ''}>&lsaquo;</button>
    <span>Page ${page}/${totalPages}</span>
    <button onclick="_callsPageNav('${tableId}',1)" style="background:none;border:1px solid var(--border);border-radius:4px;color:var(--text-2);cursor:pointer;padding:2px 8px;font-size:11px;" ${page >= totalPages ? 'disabled' : ''}>&rsaquo;</button>
  </div>` : '';

  return `<div style="margin-top:10px;font-size:11px;color:var(--text-3);font-weight:600;text-transform:uppercase;letter-spacing:0.3px;margin-bottom:4px;">Recent Calls</div>
    <table class="settings-table"><thead><tr><th>Time</th><th>Model</th><th>In</th><th>Out</th><th>Latency</th><th>Status</th></tr></thead><tbody>
    ${pageItems.map(c => `<tr>
      <td>${fmtTime(c.timestamp)}</td>
      <td>${esc(MODEL_DISPLAY_NAMES[c.model] || c.model || '-')}</td>
      <td>${c.input_tokens || '-'}</td>
      <td>${c.output_tokens || '-'}</td>
      <td>${c.latency_s ? c.latency_s + 's' : '-'}</td>
      <td class="${c.ok ? 'td-ok' : 'td-err'}">${c.ok ? 'OK' : 'ERR'}</td>
    </tr>`).join('')}
    </tbody></table>${pagerHtml}`;
}

function _callsPageNav(tableId, delta) {
  _callsPageState[tableId] = (_callsPageState[tableId] || 1) + delta;
  renderSettingsTab();
}

function fmtPriceBadge(m, modelKey) {
  const onclick = modelKey ? ` onclick="openPriceOverlay('${modelKey}',event)" style="cursor:pointer;"` : '';
  if (m.free_tier) return `<span class="settings-badge free"${onclick}>Free</span>`;
  if (m.input_price > 0 || m.output_price > 0) {
    return `<span class="settings-badge paid"${onclick}>${_pricePairStr(m.input_price, m.output_price)}</span>`;
  }
  return `<span class="settings-badge paid"${onclick}>Paid</span>`;
}
function fmtProviderPriceInner(m) {
  if (m.free_tier) return '<span class="price-inner free">Free</span>';
  if (m.input_price > 0 || m.output_price > 0) {
    return `<span class="price-inner paid">${_pricePairStr(m.input_price, m.output_price)}</span>`;
  }
  return '';
}
function _convertPrice(usdAmount) {
  if (displayCurrency === 'USD') return usdAmount;
  const info = (usageData.rates || {})[displayCurrency];
  if (!info) return usdAmount;
  return usdAmount * info.rate;
}
function _priceStr(usdAmount) {
  const converted = _convertPrice(usdAmount);
  const info = (usageData.rates || {})[displayCurrency];
  const sym = info ? info.symbol : '$';
  const prec = info ? Math.max(info.precision, 0) : 2;
  return sym + converted.toFixed(prec);
}
function _pricePairStr(usdIn, usdOut) {
  const ci = _convertPrice(usdIn);
  const co = _convertPrice(usdOut);
  const info = (usageData.rates || {})[displayCurrency];
  const sym = info ? info.symbol : '$';
  const prec = info ? Math.max(info.precision, 0) : 2;
  return sym + ci.toFixed(prec) + ',' + sym + co.toFixed(prec) + '/M';
}
function fmtProviderName(raw) {
  if (!raw) return '';
  if (raw !== raw.toLowerCase()) return raw;
  return raw.charAt(0).toUpperCase() + raw.slice(1);
}
function fmtTokens(n) { return n >= 1000 ? (n / 1000).toFixed(1) + 'k' : String(n); }
function fmtTime(ts) { if (!ts) return '-'; const d = new Date(ts * 1000); return d.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'}); }
function maskKey(k) { if (!k || k.length < 8) return '••••'; return k.slice(0, 4) + '••••' + k.slice(-4); }

let _provOrderState = null;
function openProviderOrderOverlay(modelName) {
  const models = usageData.models || {};
  const m = models[modelName];
  if (!m || !m.providers || m.providers.length < 2) return;

  _provOrderState = { model: modelName, providers: [...m.providers], selected: 0 };
  const overlay = document.createElement('div');
  overlay.className = 'sub-overlay';
  overlay.id = 'prov-order-overlay';
  overlay.onclick = (e) => { if (e.target === overlay) closeProviderOrderOverlay(); };
  _renderProvOrderOverlay(overlay);
  document.body.appendChild(overlay);
}

function _renderProvOrderOverlay(overlay) {
  if (!overlay) overlay = document.getElementById('prov-order-overlay');
  if (!overlay || !_provOrderState) return;
  const s = _provOrderState;
  overlay.innerHTML = `<div class="sub-panel">
    <div class="sub-panel-header">
      <span>Provider Priority: ${esc(MODEL_DISPLAY_NAMES[s.model] || s.model)}</span>
      <button onclick="closeProviderOrderOverlay()" style="background:none;border:none;color:var(--text-3);cursor:pointer;font-size:16px;"><i class="bx bx-x"></i></button>
    </div>
    <div class="sub-panel-list">
      ${s.providers.map((p, i) => {
        const vendor = p.split('-')[0];
        const logo = PROVIDER_LOGOS[vendor] ? '<img src="' + PROVIDER_LOGOS[vendor] + '" style="width:14px;height:14px;border-radius:2px;">' : '';
        return `<div class="sub-panel-item${i === s.selected ? ' selected' : ''}" onclick="_provOrderState.selected=${i};_renderProvOrderOverlay()">${logo} <span style="flex:1">${esc(p)}</span><span style="color:var(--text-3);font-size:10px;">#${i + 1}</span></div>`;
      }).join('')}
    </div>
    <div class="sub-panel-actions">
      <button onclick="_moveProvider(-Infinity)"><i class="bx bx-arrow-to-top"></i> Top</button>
      <button onclick="_moveProvider(-1)"><i class="bx bx-up-arrow-alt"></i> Up</button>
      <button onclick="_moveProvider(1)"><i class="bx bx-down-arrow-alt"></i> Down</button>
      <button onclick="_moveProvider(Infinity)"><i class="bx bx-arrow-to-bottom"></i> Bottom</button>
    </div>
  </div>`;
}

function _moveProvider(dir) {
  const s = _provOrderState;
  if (!s) return;
  const i = s.selected;
  const arr = s.providers;
  if (dir === -Infinity) { const [item] = arr.splice(i, 1); arr.unshift(item); s.selected = 0; }
  else if (dir === Infinity) { const [item] = arr.splice(i, 1); arr.push(item); s.selected = arr.length - 1; }
  else if (dir === -1 && i > 0) { [arr[i], arr[i-1]] = [arr[i-1], arr[i]]; s.selected = i - 1; }
  else if (dir === 1 && i < arr.length - 1) { [arr[i], arr[i+1]] = [arr[i+1], arr[i]]; s.selected = i + 1; }
  _renderProvOrderOverlay();
}

/* openBenchOverlay is defined above near BENCH_SHORT/BENCH_LABELS */

function openPriceOverlay(modelName, e) {
  if (e) e.stopPropagation();
  const models = usageData.models || {};
  const allModels = Object.entries(models).sort((a, b) => {
    const ai = a[1].free_tier ? 0 : (a[1].input_price || 0);
    const bi = b[1].free_tier ? 0 : (b[1].input_price || 0);
    return ai - bi;
  });
  if (allModels.length < 2) return;

  const overlay = document.createElement('div');
  overlay.className = 'sub-overlay';
  overlay.id = 'price-overlay';
  overlay.onclick = (e) => { if (e.target === overlay) { overlay.remove(); } };

  const labels = allModels.map(([k, m]) => MODEL_DISPLAY_NAMES[k] || k);
  const inputPrices = allModels.map(([, m]) => m.free_tier ? 0 : _convertPrice(m.input_price || 0));
  const outputPrices = allModels.map(([, m]) => m.free_tier ? 0 : _convertPrice(m.output_price || 0));
  const hlColors = allModels.map(([k]) => k === modelName ? 0.9 : 0.4);

  overlay.innerHTML = `<div class="sub-panel" style="width:500px;max-height:500px;">
    <div class="sub-panel-header"><span>Price Comparison (${displayCurrency}/1M tokens)</span><button onclick="this.closest('.sub-overlay').remove()" style="background:none;border:none;color:var(--text-3);cursor:pointer;font-size:16px;"><i class="bx bx-x"></i></button></div>
    <div style="padding:16px;flex:1;"><canvas id="price-chart"></canvas></div>
  </div>`;
  document.body.appendChild(overlay);

  const ctx = document.getElementById('price-chart').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Input', data: inputPrices, backgroundColor: hlColors.map(a => `rgba(74,222,128,${a})`), borderRadius: 4 },
        { label: 'Output', data: outputPrices, backgroundColor: hlColors.map(a => `rgba(251,191,36,${a})`), borderRadius: 4 },
      ]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: true, labels: { color: 'var(--text-2)', font: { size: 11 } } } },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: 'var(--text-3)', font: { size: 11 } } },
        y: { grid: { display: false }, ticks: { color: 'var(--text-2)', font: { size: 11, family: 'Inter' } } }
      }
    }
  });
}

function closeProviderOrderOverlay() {
  const overlay = document.getElementById('prov-order-overlay');
  if (overlay) overlay.remove();
  if (_provOrderState) {
    const models = usageData.models || {};
    if (models[_provOrderState.model]) {
      models[_provOrderState.model].providers = _provOrderState.providers;
    }
    _provOrderState = null;
    renderSettingsTab();
  }
}

function toggleKeyInput(el) {
  const form = el.classList?.contains('settings-key-form') ? el : el.parentElement.querySelector('.settings-key-form');
  if (!form) return;
  const hidden = form.style.display === 'none';
  form.style.display = hidden ? '' : 'none';
  if (hidden) form.querySelector('.settings-key-input')?.focus();
}

const _guideCache = {};
async function _loadProviderGuide(vendor) {
  if (_guideCache[vendor]) return _guideCache[vendor];
  try {
    const resp = await fetch('/api/provider/guide', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({vendor}),
    });
    const data = await resp.json();
    if (data.ok && data.guide) {
      _guideCache[vendor] = data.guide;
      return data.guide;
    }
  } catch (e) {}
  return { name: vendor, url: '', steps: ['Visit the provider website', 'Create an API key', 'Paste it above'], notes: '' };
}

async function showProviderGuide(vendor) {
  const guide = await _loadProviderGuide(vendor);
  let overlay = document.getElementById('provider-guide-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'provider-guide-overlay';
    overlay.className = 'sub-overlay';
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
    document.body.appendChild(overlay);
  }
  const notesHtml = guide.notes ? `<div style="margin-top:8px;padding:8px 12px;background:var(--surface-2);border-radius:6px;font-size:11.5px;color:var(--text-3);">${esc(guide.notes)}</div>` : '';
  overlay.innerHTML = `<div class="sub-panel" style="max-width:420px;">
    <div class="sub-panel-header"><span>Setup Guide: ${esc(guide.name)}</span><button onclick="this.closest('.sub-overlay').remove()" style="background:none;border:none;color:var(--text-3);cursor:pointer;font-size:16px;"><i class="bx bx-x"></i></button></div>
    <div style="padding:12px 16px;">
      <ol style="margin:0;padding-left:20px;font-size:12.5px;line-height:1.8;color:var(--text);">
        ${guide.steps.map(s => '<li style="margin-bottom:4px;">' + s + '</li>').join('')}
      </ol>
      ${notesHtml}
    </div>
  </div>`;
}

function _setKeyStatus(status, html) {
  status.innerHTML = html;
  status.style.display = html ? 'block' : 'none';
}

async function validateAndSaveKey(btn) {
  const form = btn.closest('.settings-key-form');
  const container = btn.closest('.settings-add-key');
  const vendor = container.dataset.vendor;
  const input = form.querySelector('.settings-key-input');
  const status = form.querySelector('.settings-key-status');
  const key = input.value.trim();
  if (!key) { _setKeyStatus(status, '<span style="color:var(--red)">Enter a key</span>'); return; }
  btn.disabled = true;
  _setKeyStatus(status, '<span style="color:var(--text-3)">Validating...</span>');
  try {
    const res = await fetch('/api/key/validate', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({vendor, key}) });
    const data = await res.json();
    if (data.ok) {
      const saveRes = await fetch('/api/key/save', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({vendor, key}) });
      const saveData = await saveRes.json();
      if (saveData.ok) {
        _setKeyStatus(status, '<span style="color:var(--green)"><i class="bx bx-check"></i> Saved</span>');
        input.value = '';
        setTimeout(() => { form.style.display = 'none'; _setKeyStatus(status, ''); fetchUsageData().then(() => renderSettingsTab()); }, 1200);
      } else {
        _setKeyStatus(status, `<span style="color:var(--red)">Save failed: ${esc(saveData.error)}</span>`);
      }
    } else {
      _setKeyStatus(status, `<span style="color:var(--red)"><i class="bx bx-x"></i> ${esc(data.error)}</span>`);
    }
  } catch (e) {
    _setKeyStatus(status, `<span style="color:var(--red)">Network error</span>`);
  }
  btn.disabled = false;
}

async function deleteApiKey(vendor, btn) {
  if (!confirm('Delete this API key?')) return;
  try {
    const res = await fetch('/api/key/delete', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({vendor}) });
    const data = await res.json();
    if (data.ok) {
      fetchUsageData().then(() => renderSettingsTab());
    }
  } catch (e) { console.warn('Delete key failed:', e); }
}

async function reverifyKey(vendor, keyId, btn) {
  btn.disabled = true;
  btn.innerHTML = '<i class="bx bx-loader-alt bx-spin" style="font-size:11px;vertical-align:middle;"></i> Verifying';
  try {
    const res = await fetch('/api/key/reverify', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({vendor, key_id: keyId}) });
    const data = await res.json();
    if (data.ok) {
      fetchUsageData().then(() => renderSettingsTab());
    } else {
      btn.innerHTML = `<i class='bx bx-x' style='font-size:11px;vertical-align:middle;'></i> ${esc(data.error || 'Failed')}`;
      setTimeout(() => { btn.innerHTML = '<i class="bx bx-refresh" style="font-size:11px;vertical-align:middle;"></i> Verify'; btn.disabled = false; }, 2000);
    }
  } catch (e) {
    btn.innerHTML = '<i class="bx bx-x" style="font-size:11px;vertical-align:middle;"></i> Error';
    setTimeout(() => { btn.innerHTML = '<i class="bx bx-refresh" style="font-size:11px;vertical-align:middle;"></i> Verify'; btn.disabled = false; }, 2000);
  }
}
