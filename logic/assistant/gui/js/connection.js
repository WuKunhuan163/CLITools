/* ── Connection Watchdog ── */
let _connWatchdogTimer = null;
let _connHealthInterval = null;
const _CONN_TIMEOUT_MS = 30000;
const _CONN_HEALTH_MS = 5000;

function _startConnectionWatchdog() {
  _clearConnectionWatchdog();
  _connWatchdogTimer = setTimeout(() => {
    _clearConnectionWatchdog();
    engine.showModelTimeoutError();
    engine.enqueueEvent({ type: 'system_notice', text: 'Connection timeout: unable to reach the model provider after 30s.', level: 'error' });
    engine.enqueueEvent({ type: 'complete', reason: 'error' });
    setStopMode(false);
    sending = false;
  }, _CONN_TIMEOUT_MS);
  _connHealthInterval = setInterval(async () => {
    try {
      const ctrl = new AbortController();
      const tid = setTimeout(() => ctrl.abort(), 3000);
      const r = await fetch('/api/health', { signal: ctrl.signal });
      clearTimeout(tid);
      if (!r.ok) throw new Error('unhealthy');
    } catch (e) {
      _clearConnectionWatchdog();
      engine.showNetworkError();
      engine.enqueueEvent({ type: 'system_notice', text: 'Network connection lost. Check your connection and try again.', level: 'error' });
      engine.enqueueEvent({ type: 'complete', reason: 'error' });
      setStopMode(false);
      sending = false;
    }
  }, _CONN_HEALTH_MS);
}
function _clearConnectionWatchdog() {
  if (_connWatchdogTimer) { clearTimeout(_connWatchdogTimer); _connWatchdogTimer = null; }
  if (_connHealthInterval) { clearInterval(_connHealthInterval); _connHealthInterval = null; }
}

/* ── SSE Connection ── */
function connectSSE() {
  const source = new EventSource('/api/events');

  source.onmessage = function(e) {
    try {
      const evt = JSON.parse(e.data);
      handleSSEEvent(evt);
    } catch (err) {
      console.warn('SSE parse error:', err);
    }
  };

  source.onerror = function() {
    console.warn('SSE connection lost, will check server health...');
    source.close();
    _checkServerHealth();
  };
}

let _serverWasDown = false;
function _setConnectionStatus(offline) {
  let banner = document.getElementById('conn-status-banner');
  if (offline) {
    if (!banner) {
      banner = document.createElement('div');
      banner.id = 'conn-status-banner';
      banner.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:9999;background:var(--red);color:#fff;text-align:center;padding:4px 8px;font-size:12px;font-weight:500;';
      banner.innerHTML = '<i class="bx bx-wifi-off" style="vertical-align:middle;margin-right:4px;"></i> Server disconnected. Reconnecting...';
      document.body.appendChild(banner);
    }
  } else if (banner) {
    banner.remove();
  }
}
function _checkServerHealth() {
  fetch('/api/sessions').then(r => {
    if (r.ok && _serverWasDown) {
      console.log('Server is back — reloading page');
      _setConnectionStatus(false);
      location.reload();
    } else {
      _serverWasDown = false;
      _setConnectionStatus(false);
      syncSessions();
      setTimeout(connectSSE, 2000);
    }
  }).catch(() => {
    _serverWasDown = true;
    _setConnectionStatus(true);
    setTimeout(_checkServerHealth, 3000);
  });
}

function syncSessions() {
  fetch('/api/sessions').then(r => r.json()).then(data => {
    if (!data.ok || !data.sessions) return;
    window._allSessions = data.sessions;
    const backendIds = new Set();
    let needRefresh = false;
    data.sessions.forEach(s => {
      backendIds.add(s.id);
      const existing = engine.getSession(s.id);
      if (!existing) {
        const ts = s.created_at ? s.created_at * 1000 : Date.now();
        engine.sessions[s.id] = {
          id: s.id, title: s.title || 'New Task',
          status: s.status || 'idle', mode: s.mode || 'agent',
          createdAt: ts,
        };
        if (s.done_reason) engine.sessions[s.id].doneReason = s.done_reason;
        if (!engine.activeSessionId) engine.activeSessionId = s.id;
        needRefresh = true;
      } else {
        if (existing.status !== s.status || existing.doneReason !== s.done_reason) {
          existing.status = s.status;
          if (s.done_reason) existing.doneReason = s.done_reason;
          else delete existing.doneReason;
          needRefresh = true;
        }
        if (existing.title !== s.title) {
          existing.title = s.title;
          needRefresh = true;
        }
      }
    });
    Object.keys(engine.sessions).forEach(id => {
      if (!backendIds.has(id)) { delete engine.sessions[id]; needRefresh = true; }
    });
    if (needRefresh) engine._refreshSessions();
    if (!activeSessionId && data.sessions.length > 0) {
      const first = data.sessions[0];
      activeSessionId = first.id;
      engine.activeSessionId = first.id;
      engine._refreshSessions();
      $('main-title').textContent = first.title || 'New Task';
      apiActivateSession(first.id);
    }
  }).catch(() => {});
}
setInterval(syncSessions, 10000);

function handleSSEEvent(evt) {
  if (_activatingSessionLock && evt.session_id === _activatingSessionLock
      && evt.type !== 'session_created' && evt.type !== 'session_deleted') {
    _sseBufferDuringActivation.push(evt);
    return;
  }

  const welcome = $('welcome');
  if (welcome) welcome.remove();

  const _watchdogClearTypes = new Set([
    'session_status', 'model_decision_start', 'model_decision_end',
    'model_confirmed', 'llm_request', 'llm_response_start', 'text',
    'stream_start', 'tool_start', 'complete',
  ]);
  if (_connWatchdogTimer && _watchdogClearTypes.has(evt.type)) {
    _clearConnectionWatchdog();
  }

  const _globalEventTypes = new Set([
    'session_created', 'session_renamed', 'session_deleted', 'session_status',
    'settings_changed', 'settings_open', 'settings_close',
    'inject_input', 'model_switched', 'mode_switch_resolved',
    'queue_updated', 'turn_limit_set', 'queue_task_started',
    'workspace_created', 'workspace_opened', 'workspace_closed',
    'cancel_requested',
  ]);
  if (!_globalEventTypes.has(evt.type) && evt.session_id && evt.session_id !== activeSessionId) {
    return;
  }

  switch (evt.type) {
    case 'session_created':
      if (!engine.getSession(evt.id)) {
        engine.addSession(evt.id, evt.title || 'New Task', 'idle', evt.mode || 'agent');
      }
      activeSessionId = evt.id;
      engine.activeSessionId = evt.id;
      engine.clearAllTrackers();
      engine._refreshSessions();
      $('main-title').textContent = evt.title || 'New Task';
      engine._selfOperate = !!evt.self_operate;
      if (engine.sessions[evt.id]) {
        engine.sessions[evt.id].selfOperate = !!evt.self_operate;
      }
      apiActivateSession(evt.id).then(() => {
        if (engine._selfOperate) {
          $('input').disabled = false;
          $('input').placeholder = 'Self-operate mode \u2014 type to queue, response via CLI...';
          _autoResizeInput();
          setStopMode(true);
        }
      });
      { const m = evt.mode || 'agent';
        if (m !== selectedMode) {
          selectedMode = m;
          if (modePill && modePill.setValue) modePill.setValue(m);
        }
      }
      break;

    case 'session_renamed':
      engine.renameSession(evt.id, evt.title, true);
      if (evt.id === activeSessionId) {
        $('main-title').textContent = evt.title;
      }
      break;

    case 'session_deleted':
      engine.deleteSession(evt.id);
      if (!engine.activeSessionId) {
        activeSessionId = null;
        $('main-title').textContent = 'New Task';
        $('chat-area').innerHTML = '<div id="welcome" class="welcome"><p>Type a message to start</p></div>';
        $('input').disabled = false;
        $('input').placeholder = 'Type a message...';
        _autoResizeInput();
        $('btn-send').disabled = false;
        setStopMode(false);
      }
      break;

    case 'cancel_requested':
      engine._selfOperate = false;
      $('input').disabled = false;
      $('input').placeholder = _('Type a message. Ctrl+Enter to send.');
      _autoResizeInput();
      $('btn-send').disabled = false;
      break;

    case 'settings_changed':
      fetchUsageData().then(() => { if (settingsTab) renderSettingsTab(); });
      break;

    case 'session_status':
      engine.setSessionStatus(evt.id, evt.status, evt.reason);
      if (evt.id === activeSessionId) {
        if (evt.status === 'done' || evt.status === 'idle') {
          sending = false;
          $('input').focus();
          setStopMode(false);
        } else if (evt.status === 'running') {
          setStopMode(true);
        }
      }
      break;

    case 'inject_input': {
      const input = $('input');
      const text = evt.text || '';
      input.value = '';
      input.disabled = false;
      let i = 0;
      const typeInterval = setInterval(() => {
        if (i < text.length) {
          input.value += text[i];
          i++;
        } else {
          clearInterval(typeInterval);
          setTimeout(() => sendMessage(), 200);
        }
      }, 30);
      break;
    }

    case 'model_switched': {
      if (modelPill) modelPill.setValue(evt.to);
      break;
    }

    case 'mode_switch_resolved': {
      if (evt.decision === 'allow' && evt.target_mode) {
        selectedMode = evt.target_mode;
        if (modePill && modePill.setValue) modePill.setValue(evt.target_mode);
      }
      engine.enqueueEvent(evt);
      break;
    }

    case 'system_notice':
    case 'model_decision_end':
    case 'model_decision_proposed':
    case 'model_decision_start':
      engine.enqueueEvent(evt);
      break;

    case 'model_confirmed': {
      if (evt.provider) {
        selectedModel = evt.provider;
      }
      engine.enqueueEvent(evt);
      break;
    }

    case 'settings_open': {
      openSettings(evt.tab || '');
      break;
    }
    case 'settings_close': {
      closeSettings();
      break;
    }
    case 'debug_mode': {
      setDebugModeTo(!!evt.enabled);
      break;
    }

    case 'workspace_created':
    case 'workspace_opened': {
      if (evt.path) {
        currentWorkspace = evt.path;
        localStorage.setItem('workspace_path', evt.path);
        _updateWorkspaceIndicator(evt.path);
      }
      break;
    }
    case 'workspace_closed': {
      currentWorkspace = '';
      localStorage.removeItem('workspace_path');
      _updateWorkspaceIndicator();
      break;
    }

    case 'queue_updated': {
      _queuedTasks = evt.queue || [];
      _updateQueueBadge();
      _renderQueueContainer();
      break;
    }

    case 'turn_limit_set': {
      const tl = evt.turn_limit || 0;
      selectedTurnLimit = tl;
      if (turnLimitPill) turnLimitPill.setValue(tl);
      break;
    }

    case 'queue_task_started': {
      if (evt.mode) {
        selectedMode = evt.mode;
        const modeBtn = document.getElementById('mode-pill');
        if (modeBtn) modeBtn.setValue(evt.mode);
        const modeBtns = document.querySelectorAll('[data-mode]');
        modeBtns.forEach(b => b.classList.toggle('active', b.dataset.mode === evt.mode));
      }
      if (evt.model && modelPill) {
        selectedModel = evt.model;
        modelPill.setValue(evt.model);
      }
      const taskPreview = evt.text ? `: ${evt.text}` : '';
      engine.enqueueEvent({type: 'notice', level: 'info',
        icon: 'bx-play-circle',
        message: `Starting queued task${taskPreview} (${evt.remaining || 0} remaining)`});
      break;
    }

    case 'error': {
      _clearConnectionWatchdog();
      engine._clearPendingModelBanner();
      const errMsg = evt.message || 'Unknown error';
      engine.renderCenterNotice(`<i class="bx bx-x-circle" style="color:var(--status-error);font-size:16px;vertical-align:middle;"></i> <strong style="color:var(--status-error);">Error</strong>: ${esc(errMsg)}`);
      $('input').disabled = false;
      $('btn-send').disabled = false;
      sending = false;
      setStopMode(false);
      const errorSid = evt.session_id || activeSessionId;
      if (errorSid) engine.setSessionStatus(errorSid, 'done', 'error');
      break;
    }

    default:
      if (evt.type === 'user' && evt.session_id) {
        if (engine._localUserPending) { engine._localUserPending = false; break; }
      }
      if (evt.type === 'llm_request' && evt.self_operate) {
        if (!engine._selfOperate) {
          engine.enqueueEvent({type: 'notice', level: 'info',
            icon: 'bx-transfer-alt',
            message: 'Switched to Self-operate mode'});
        }
        engine._selfOperate = true;
        if (engine.activeSessionId && engine.sessions[engine.activeSessionId]) {
          engine.sessions[engine.activeSessionId].selfOperate = true;
        }
        $('input').placeholder = 'Self-operate mode \u2014 type to queue, response via CLI...';
        _autoResizeInput();
      } else if (evt.type === 'llm_request' && !evt.self_operate && engine._selfOperate) {
        engine._selfOperate = false;
        if (engine.activeSessionId && engine.sessions[engine.activeSessionId]) {
          engine.sessions[engine.activeSessionId].selfOperate = false;
        }
        engine.enqueueEvent({type: 'notice', level: 'info',
          icon: 'bx-transfer-alt',
          message: 'Switched to Model Provider'});
        $('input').placeholder = _('Type a message. Ctrl+Enter to send.');
        _autoResizeInput();
      }
      if (evt.type === 'complete') {
        const reason = evt.reason || 'done';
        const completeSid = evt.session_id || activeSessionId;
        if (completeSid) engine.setSessionStatus(completeSid, 'done', reason);
        if (!evt.session_id || evt.session_id === activeSessionId) {
          _clearConnectionWatchdog();
          engine._clearPendingModelBanner();
          sending = false;
          engine._selfOperate = false;
          $('input').disabled = false;
          $('input').placeholder = _('Type a message. Ctrl+Enter to send.');
          _autoResizeInput();
          $('btn-send').disabled = false;
          setStopMode(false);
        }
      }
      engine.enqueueEvent(evt);
      break;
  }
}
