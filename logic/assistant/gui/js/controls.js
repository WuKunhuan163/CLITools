const engine = new AgentGUIEngine({
  chatArea: $('chat-area'),
  todoListEl: $('todo-list'),
  execListEl: $('exec-list'),
  callListEl: $('call-list'),
  execPanel: $('exec-panel'),
  callPanel: $('call-panel'),
  todoPanel: $('todo-panel'),
  sessionListEl: $('session-list'),
});
engine.setDebugMode(false, createDebugBlock);
fetch('/api/state').then(r => r.json()).then(d => {
  if (d.ok && d.state) {
    engine._maxContextTokens = d.state.effective_context_limit || d.state.max_context_tokens || 0;
    engine._rawMaxContextTokens = d.state.max_context_tokens || 0;
  }
}).catch(() => {});
{ const saved = parseInt(localStorage.getItem('maxRoundHistory')); if (saved > 0) engine.setMaxRoundHistory(saved); }

const modePill = buildPillSelect(
  $('mode-pill'),
  Object.keys(MODE_ICONS).map(k => ({ value: k, label: MODE_LABELS[k], icon: MODE_ICONS[k] })),
  selectedMode,
  (v) => setMode(v)
);
const modelPill = buildPillSelect(
  $('model-pill'),
  MODEL_OPTIONS.map(o => o.value === 'auto' ? { value: 'auto', label: 'Auto', icon: 'bx-bot' } : { value: o.value, label: o.label, ...(MODEL_LOGOS[o.value] ? { logo: MODEL_LOGOS[o.value] } : { icon: 'bx-bot' }) }),
  selectedModel,
  (v) => setModel(v)
);
engine.onAutoModelChosen((chosenProvider) => {
  if (modelPill && modelPill.setValue) {
    modelPill.setValue(chosenProvider);
    selectedModel = chosenProvider;
  }
});

const TURN_LIMIT_PRESETS = [2, 5, 10, 20, 50, 100, 200, 500];
const turnLimitPill = (function() {
  const container = $('turn-limit-pill');
  let customValue = null;

  function buildOptions() {
    const opts = TURN_LIMIT_PRESETS.map(n => ({
      value: String(n), label: n + ' rounds', icon: 'bx-revision'
    }));
    opts.push({ value: '0', label: 'Unlimited', icon: 'bx-infinite' });
    const isPreset = selectedTurnLimit === 0 || TURN_LIMIT_PRESETS.includes(selectedTurnLimit);
    if (!isPreset && selectedTurnLimit > 0) customValue = selectedTurnLimit;
    const customLabel = customValue ? 'Custom (' + customValue + ')' : 'Custom';
    opts.push({ value: 'custom', label: customLabel, icon: 'bx-edit-alt' });
    return opts;
  }

  function currentVal() {
    if (selectedTurnLimit === 0) return '0';
    if (TURN_LIMIT_PRESETS.includes(selectedTurnLimit)) return String(selectedTurnLimit);
    return 'custom';
  }

  function render() {
    const opts = buildOptions();
    const cv = currentVal();
    const cur = opts.find(o => o.value === cv) || opts[0];
    const displayLabel = cv === 'custom' && customValue
      ? 'Custom (' + customValue + ' rounds)'
      : cur.label;

    let iconHtml = cur.icon ? `<i class="bx ${cur.icon}"></i>` : '';
    container.innerHTML =
      `<button class="pill-btn">${iconHtml} ${esc(displayLabel)}<i class="bx bx-chevron-down pill-chevron"></i></button>`
      + `<div class="pill-menu"><div class="pill-menu-items">`
      + opts.map(o => {
          let oIcon = o.icon ? `<i class="bx ${o.icon}"></i>` : '';
          return `<div class="pill-option${o.value === cv ? ' active' : ''}" data-value="${esc(o.value)}">${oIcon} ${esc(o.label)}</div>`;
        }).join('')
      + `</div></div>`;

    const btn = container.querySelector('.pill-btn');
    const menu = container.querySelector('.pill-menu');
    btn.onclick = (e) => { e.stopPropagation(); menu.classList.toggle('open'); };

    container.querySelectorAll('.pill-option').forEach(opt => {
      opt.onclick = (e) => {
        e.stopPropagation();
        const v = opt.dataset.value;
        if (v === 'custom') {
          const optEl = opt;
          const curText = customValue ? String(customValue) : '';
          optEl.innerHTML = `<i class="bx bx-edit-alt"></i> <input type="number" min="1" max="9999" class="pill-custom-input" value="${esc(curText)}" placeholder="rounds">`;
          const inp = optEl.querySelector('input');
          inp.onclick = (ev) => ev.stopPropagation();
          inp.focus();
          inp.select();
          function commit() {
            const n = parseInt(inp.value, 10);
            if (n > 0 && n <= 9999) {
              customValue = n;
              selectedTurnLimit = n;
              setTurnLimit(String(n));
            } else if (inp.value === '' || inp.value === '0') {
              selectedTurnLimit = 0;
              customValue = null;
              setTurnLimit('0');
            }
            menu.classList.remove('open');
            render();
          }
          inp.onblur = commit;
          inp.onkeydown = (ev) => { if (ev.key === 'Enter') { ev.preventDefault(); commit(); } if (ev.key === 'Escape') { menu.classList.remove('open'); render(); } };
          return;
        }
        menu.classList.remove('open');
        const nv = parseInt(v, 10) || 0;
        selectedTurnLimit = nv;
        if (nv > 0 && !TURN_LIMIT_PRESETS.includes(nv)) customValue = nv;
        setTurnLimit(v);
        render();
      };
    });
  }

  render();
  document.addEventListener('click', () => {
    const m = container.querySelector('.pill-menu');
    if (m) m.classList.remove('open');
  });
  return {
    setValue(v) { selectedTurnLimit = parseInt(v, 10) || 0; render(); },
    render
  };
})();

const _sessionDrafts = {};

engine.onSessionChange((action, session) => {
  if (action === 'activate' && session) {
    const inputEl = $('input');
    if (activeSessionId && inputEl) {
      _sessionDrafts[activeSessionId] = inputEl.value;
    }
    activeSessionId = session.id;
    $('main-title').textContent = session.title;
    _updateWorkspaceIndicator();

    const isSelfOp = !!session.selfOperate;
    engine._selfOperate = isSelfOp;
    if (isSelfOp && session.status === 'running') {
      inputEl.placeholder = 'Self-operate mode \u2014 type to queue, response via CLI...';
    } else {
      inputEl.disabled = false;
      inputEl.placeholder = _('Type a message. Ctrl+Enter to send.');
      $('btn-send').disabled = false;
    }

    apiActivateSession(session.id);
    if (inputEl) {
      inputEl.value = _sessionDrafts[session.id] || '';
      inputEl.style.height = 'auto';
      inputEl.style.height = inputEl.scrollHeight + 'px';
    }
    const sessionMode = session.mode || 'agent';
    if (sessionMode !== selectedMode) {
      selectedMode = sessionMode;
      if (modePill && modePill.setValue) modePill.setValue(sessionMode);
    }
  } else if (action === 'rename' && session) {
    if (session.id === activeSessionId) {
      $('main-title').textContent = session.title;
    }
  } else if (action === 'delete' && session && session.id) {
    fetch('/api/session/' + session.id, { method: 'DELETE' })
      .then(r => r.json())
      .then(data => {
        if (data.ok) {
          delete _sessionDrafts[session.id];
          if (activeSessionId === session.id || !activeSessionId) {
            const remaining = engine.listSessions();
            if (remaining.length > 0) {
              engine.setActiveSession(remaining[0].id);
              activeSessionId = remaining[0].id;
            } else {
              createNewSession();
            }
          }
        }
      }).catch(() => {});
  }
});

/* ── Keyboard Shortcuts ── */
$('input').addEventListener('keydown', function(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault();
    sendMessage();
    return;
  }
  if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
    e.preventDefault();
    sendMessage();
    return;
  }
});
function _autoResizeInput() {
  const el = $('input');
  el.style.height = 'auto';
  const contentH = el.scrollHeight;
  let h = contentH;
  if (!el.value) {
    const m = document.createElement('div');
    const cs = getComputedStyle(el);
    m.style.cssText = 'position:absolute;visibility:hidden;white-space:pre-wrap;word-wrap:break-word;'
      + 'font:' + cs.font + ';padding:' + cs.padding + ';border:' + cs.border
      + ';width:' + cs.width + ';box-sizing:' + cs.boxSizing + ';';
    m.textContent = el.placeholder;
    document.body.appendChild(m);
    h = Math.max(h, m.offsetHeight);
    document.body.removeChild(m);
  }
  el.style.height = Math.min(h, 160) + 'px';
}
$('input').addEventListener('input', _autoResizeInput);
window.addEventListener('resize', _autoResizeInput);
