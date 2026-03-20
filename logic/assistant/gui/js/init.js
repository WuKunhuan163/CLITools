/* ── Init ── */
async function init() {
  try {
    if (localStorage.getItem('debug_mode') === '1') {
      setDebugModeTo(true);
    }
  } catch(e) {}

  try {
    const scopeResp = await fetch('/api/scope');
    const scopeData = await scopeResp.json();
    if (scopeData.ok && scopeData.scope_name) {
      const sn = scopeData.scope_name;
      document.title = sn + ' Assistant';
      const st = document.getElementById('sidebar-title');
      if (st) st.textContent = sn + ' Assistant';
      const sf = document.getElementById('sidebar-footer');
      if (sf) sf.textContent = sn + ' Assistant';
    }
    if (scopeData.ok && scopeData.workspace_path) {
      if (!currentWorkspace) {
        currentWorkspace = scopeData.workspace_path;
      }
      _updateWorkspaceIndicator(currentWorkspace || scopeData.workspace_path);
    } else if (currentWorkspace) {
      _updateWorkspaceIndicator();
    }
  } catch (e) { /* keep defaults */ }

  if (!currentWorkspace) {
    try {
      const wsResp = await fetch('/api/workspace/active');
      const wsData = await wsResp.json();
      if (wsData.ok && wsData.workspace && wsData.workspace.path) {
        currentWorkspace = wsData.workspace.path;
        localStorage.setItem('workspace_path', currentWorkspace);
        _updateWorkspaceIndicator(currentWorkspace);
      }
    } catch (e) {}
  }

  let initialSessionId = null;
  const _hashMatch = location.hash.match(/session=([a-f0-9]+)/);
  const _qpMatch = new URLSearchParams(location.search).get('activate');
  const _requestedSid = _hashMatch ? _hashMatch[1] : (_qpMatch || null);

  try {
    const resp = await fetch('/api/sessions');
    const data = await resp.json();
    if (data.ok && data.sessions) {
      window._allSessions = data.sessions;
      let runningId = null;
      const sessionIds = new Set();
      data.sessions.forEach(s => {
        sessionIds.add(s.id);
        const ts = s.created_at ? s.created_at * 1000 : Date.now();
        engine.addSession(s.id, s.title, s.status, s.mode || 'agent', s.done_reason, ts);
        if (s.status === 'running') runningId = s.id;
        if (!initialSessionId) initialSessionId = s.id;
      });
      if (_requestedSid && sessionIds.has(_requestedSid)) {
        initialSessionId = _requestedSid;
      } else if (_requestedSid) {
        const prefix = data.sessions.find(s => s.id.startsWith(_requestedSid));
        if (prefix) initialSessionId = prefix.id;
      }
      if (runningId && !_requestedSid) initialSessionId = runningId;
      const initSession = data.sessions.find(s => s.id === initialSessionId);
      if (initSession && initSession.mode && initSession.mode !== selectedMode) {
        selectedMode = initSession.mode;
        if (modePill && modePill.setValue) modePill.setValue(initSession.mode);
      }
    }
  } catch (err) {
    console.warn('Failed to load sessions:', err);
  }

  async function _loadModels(retries) {
    for (let i = 0; i < retries; i++) {
      try {
        const cfgResp = await fetch('/api/model/list');
        const cfgData = await cfgResp.json();
        if (cfgData.ok && cfgData.models && cfgData.models.length > 1) {
          MODEL_OPTIONS = cfgData.models.map(m => ({ value: m.value, label: m.label, logo: m.logo || null, status: m.status || 'available' }));
          window._configuredModels = cfgData.models.filter(m => m.value !== 'auto' && m.status === 'available').map(m => ({id: m.value, display: m.label}));
          window._modelPricing = {};
          cfgData.models.forEach(m => {
            if (m.value !== 'auto') {
              window._modelPricing[m.value] = {
                free_tier: m.free_tier || false,
                input_per_1m: m.input_price_per_1m || 0,
                output_per_1m: m.output_price_per_1m || 0,
                currency: m.currency || 'USD',
              };
            }
          });
          const newOpts = MODEL_OPTIONS.map(m => {
            if (m.value === 'auto') return { value: 'auto', label: _('Auto'), icon: 'bx-bot', status: 'available' };
            const logo = m.logo || MODEL_LOGOS[m.value] || resolveModelLogo(m.value);
            return { value: m.value, label: m.label, status: m.status || 'available', ...(logo ? { logo } : { icon: 'bx-bot' }) };
          });
          modelPill.setOptions(newOpts);
          if (_queuedTasks.length) _renderQueueContainer();
          return;
        }
      } catch (e) { /* retry */ }
      await new Promise(r => setTimeout(r, 1000 * (i + 1)));
    }
  }
  await Promise.all([_loadModelsMeta(), _loadI18N(), _loadPalette()]);
  applyTheme(currentTheme);
  await _loadModels(3);

  try {
    const mst = await fetch('/api/model/state').then(r => r.json());
    if (mst.ok) {
      selectedModel = mst.selected_model || 'auto';
      selectedMode = mst.selected_mode || 'agent';
      selectedTurnLimit = mst.selected_turn_limit || 20;
      if (modelPill) modelPill.setValue(selectedModel);
      if (modePill) modePill.setValue(selectedMode);
      if (turnLimitPill) turnLimitPill.setValue(selectedTurnLimit);
    }
  } catch (_) {
    selectedModel = selectedModel || 'auto';
    selectedMode = selectedMode || 'agent';
    selectedTurnLimit = selectedTurnLimit || 20;
  }

  try {
    const scfg = await fetch('/api/session_config').then(r => r.json());
    if (scfg.ok && scfg.config) {
      const c = scfg.config;
      if (c.default_turn_limit && selectedTurnLimit === null) {
        selectedTurnLimit = c.default_turn_limit;
        if (turnLimitPill) turnLimitPill.setValue(c.default_turn_limit);
      }
    }
    if (scfg.ok && scfg.schema) {
      window._sessionSettingsSchema = scfg.schema;
      for (const s of scfg.schema) {
        if (!localStorage.getItem(s.key) && scfg.config[s.key] != null) {
          localStorage.setItem(s.key, String(scfg.config[s.key]));
        }
      }
    }
    if (scfg.ok && scfg.config && window.Collapsible) {
      window.Collapsible.configure({
        collapsed_lines: parseInt(localStorage.getItem('block_collapsed_lines')) || scfg.config.block_collapsed_lines || 6,
        expanded_lines: parseInt(localStorage.getItem('block_expanded_lines')) || scfg.config.block_expanded_lines || 16,
      });
    }
  } catch (e) { console.warn('Failed to load session config:', e); }

  if (initialSessionId) {
    activeSessionId = initialSessionId;
    engine.activeSessionId = initialSessionId;
    engine._refreshSessions();
    $('main-title').textContent = engine.sessions[initialSessionId]?.title || 'New Task';
    await apiActivateSession(initialSessionId);
    try {
      const qr = await fetch(`/api/session/${initialSessionId}/queue`, {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({action:'list'})
      }).then(r => r.json());
      if (qr.ok && qr.queue) { _queuedTasks = qr.queue; _renderQueueContainer(); _updateQueueBadge(); }
    } catch(e) {}
  } else {
    $('main-title').textContent = 'New Task';
    $('chat-area').innerHTML = '<div id="welcome" class="welcome"><p>Type a message to start</p></div>';
  }

  const gate = document.getElementById('loading-gate');
  if (gate) {
    gate.style.opacity = '0';
    setTimeout(() => gate.remove(), 300);
  }

  _updateWorkspaceIndicator();
  connectSSE();
  _autoResizeInput();

  const chatArea = $('chat-area');
  chatArea.addEventListener('scroll', () => {
    if (chatArea.scrollTop <= 0 && _pendingOlderEvents.length > 0) {
      loadOlderEvents();
    }
    _updateFloatPanel();
    _userScrolledAt = Date.now();
  });

  $('input').focus();

  setInterval(() => {
    const rawIdle = localStorage.getItem('auto_scroll_idle_s');
    const idleS = rawIdle === 'none' ? 0 : (parseInt(rawIdle) || 30);
    if (idleS <= 0) return;
    const chat = $('chat-area');
    if (!chat) return;
    const atBottom = chat.scrollHeight - chat.scrollTop - chat.clientHeight < 80;
    if (atBottom) return;
    const idleMs = Date.now() - _userScrolledAt;
    if (idleMs >= idleS * 1000) {
      chat.scrollTo({ top: chat.scrollHeight, behavior: 'smooth' });
    }
  }, 5000);
}

init();
