/* ── Create New Session ── */
async function createNewSession() {
  try {
    const body = { title: 'New Task' };
    if (currentWorkspace) body.codebase_root = currentWorkspace;
    const resp = await fetch('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await resp.json();
    if (data.ok) {
      const sid = data.session_id;
      engine.addSession(sid, 'New Task', 'idle');
      engine.setActiveSession(sid);
      activeSessionId = sid;
      $('main-title').textContent = 'New Task';

      engine.chatArea.innerHTML = '';
      const welcome = document.createElement('div');
      welcome.className = 'welcome';
      welcome.id = 'welcome';
      const modeIcon = MODE_ICONS[selectedMode] || 'bx-bot';
      welcome.innerHTML = '<i class="bx ' + modeIcon + ' welcome-icon"></i><div class="welcome-text">Type a message to start</div>';
      engine.chatArea.appendChild(welcome);

      $('input').disabled = false;
      $('btn-send').disabled = false;
      sending = false;
      $('input').focus();
    }
  } catch (err) {
    console.error('New session error:', err);
  }
}

let INITIAL_ROUNDS = parseInt(localStorage.getItem('initial_rounds')) || 5;
let _pendingOlderEvents = [];
let _allSessionEvents = [];

let _activatingSessionLock = null;
let _sseBufferDuringActivation = [];
async function apiActivateSession(sid) {
  if (_activatingSessionLock === sid) return;
  _activatingSessionLock = sid;
  _sseBufferDuringActivation = [];
  const chatArea = $('chat-area');
  chatArea.innerHTML = '';
  _pendingOlderEvents = [];
  _allSessionEvents = [];
  try {
    const resp = await fetch(`/api/session/${sid}/history`);
    const data = await resp.json();
    if (data.ok && data.events && data.events.length > 0) {
      const allEvents = data.events;
      _allSessionEvents = allEvents;
      let eventsToRender = allEvents;
      const roundStarts = [];
      for (let i = 0; i < allEvents.length; i++) {
        if (allEvents[i].type === 'llm_request') roundStarts.push(i);
      }
      if (roundStarts.length > INITIAL_ROUNDS) {
        const firstRoundIdx = roundStarts[0];
        const cutIndex = roundStarts[roundStarts.length - INITIAL_ROUNDS];
        const preRoundEvents = allEvents.slice(0, firstRoundIdx);
        _pendingOlderEvents = allEvents.slice(firstRoundIdx, cutIndex);
        eventsToRender = [...preRoundEvents, ...allEvents.slice(cutIndex)];
        const foldedRounds = roundStarts.length - INITIAL_ROUNDS;
        engine.setReplayMode(true);
        for (const evt of preRoundEvents) {
          await engine.processEvent(evt);
        }
        engine.setReplayMode(false);
        const loadMoreBtn = document.createElement('div');
        loadMoreBtn.className = 'load-more-btn';
        loadMoreBtn.id = 'load-more';
        loadMoreBtn.textContent = `Load ${foldedRounds} earlier rounds`;
        loadMoreBtn.onclick = () => loadOlderEvents();
        chatArea.appendChild(loadMoreBtn);
        eventsToRender = allEvents.slice(cutIndex);
      }
      engine.setReplayMode(true);
      for (const evt of eventsToRender) {
        await engine.processEvent(evt);
      }
      engine.setReplayMode(false);
    } else {
      chatArea.innerHTML = '<div id="welcome" class="welcome"><p>Type a message to start</p></div>';
    }
  } catch (e) {
    console.warn('Failed to load session history:', e);
    chatArea.innerHTML = `<div class="welcome" style="color:var(--text-3);">
      <i class="bx bx-wifi-off welcome-icon" style="color:var(--red);font-size:28px;"></i>
      <div class="welcome-text" style="font-size:13px;">
        <strong style="color:var(--text);">Cannot reload session.</strong><br>
        Server may be unavailable. <a href="javascript:location.reload()" style="color:var(--accent);">Refresh the page</a> to reconnect.
      </div>
    </div>`;
  } finally {
    _activatingSessionLock = null;
    const buffered = _sseBufferDuringActivation;
    _sseBufferDuringActivation = [];
    for (const bEvt of buffered) {
      handleSSEEvent(bEvt);
    }
  }
}

async function loadOlderEvents() {
  if (!_pendingOlderEvents.length) return;
  const chatArea = $('chat-area');
  const scrollHeightBefore = chatArea.scrollHeight;
  const scrollTopBefore = chatArea.scrollTop;

  const roundStarts = [];
  for (let i = 0; i < _pendingOlderEvents.length; i++) {
    if (_pendingOlderEvents[i].type === 'llm_request') roundStarts.push(i);
  }
  let cutIdx = 0;
  if (roundStarts.length > INITIAL_ROUNDS) {
    cutIdx = roundStarts[roundStarts.length - INITIAL_ROUNDS];
  }
  const eventsToLoad = _pendingOlderEvents.slice(cutIdx);
  _pendingOlderEvents = _pendingOlderEvents.slice(0, cutIdx);

  const loadBtn = $('load-more');
  const insertBefore = loadBtn || chatArea.firstChild;

  const tempArea = document.createElement('div');
  const savedChatArea = engine.chatArea;
  engine.chatArea = tempArea;
  engine.setReplayMode(true);
  for (const evt of eventsToLoad) {
    await engine.processEvent(evt);
  }
  engine.setReplayMode(false);
  engine.chatArea = savedChatArea;

  while (tempArea.firstChild) {
    chatArea.insertBefore(tempArea.firstChild, insertBefore);
  }

  if (_pendingOlderEvents.length > 0 && loadBtn) {
    const remaining = _pendingOlderEvents.filter(e => e.type === 'llm_request').length;
    loadBtn.textContent = `Load ${remaining} earlier rounds`;
  } else if (loadBtn) {
    loadBtn.remove();
  }

  const scrollDelta = chatArea.scrollHeight - scrollHeightBefore;
  chatArea.scrollTop = scrollTopBefore + scrollDelta;
}
