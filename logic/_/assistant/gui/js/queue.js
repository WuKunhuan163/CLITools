/* ── Send Message ── */
let taskRunning = false;
let _userScrolledAt = 0;
let _autoScrollIdleS = localStorage.getItem('auto_scroll_idle_s') === 'none' ? 0 : (parseInt(localStorage.getItem('auto_scroll_idle_s')) || 30);
let _queuedTasks = [];

function _updateQueueBadge() {
  const btn = $('btn-send');
  const badge = btn.querySelector('.queue-badge');
  if (_queuedTasks.length > 0 && taskRunning) {
    if (!badge) {
      const b = document.createElement('span');
      b.className = 'queue-badge';
      b.textContent = _queuedTasks.length;
      btn.appendChild(b);
    } else {
      badge.textContent = _queuedTasks.length;
    }
    btn.querySelector('i').className = 'bx bx-list-plus';
  } else {
    if (badge) badge.remove();
    btn.querySelector('i').className = 'bx bx-send';
  }
}

function _renderQueueContainer() {
  const container = $('queue-container');
  if (!container) return;
  if (!_queuedTasks.length) {
    container.classList.remove('visible');
    container.innerHTML = '';
    return;
  }
  container.classList.add('visible');
  const modelOpts = (window._configuredModels || []).map(m =>
    `<option value="${m.id}">${m.display || m.id}</option>`
  ).join('');
  const modeOpts = ['agent','ask','plan'].map(m =>
    `<option value="${m}">${m.charAt(0).toUpperCase()+m.slice(1)}</option>`
  ).join('');
  const items = _queuedTasks.map((t, i) => {
    const modeSelect = `<select onchange="_queueUpdateTask('${t.id}',{mode:this.value})">${modeOpts}</select>`;
    const modelSelect = `<select onchange="_queueUpdateTask('${t.id}',{model:this.value})"><option value="auto">Auto</option>${modelOpts}</select>`;
    return `<div class="queue-item" draggable="true" data-task-id="${t.id}" data-idx="${i}"
      ondragstart="_qDragStart(event)" ondragover="_qDragOver(event)" ondragleave="_qDragLeave(event)" ondrop="_qDrop(event)">
      <span class="queue-item-grip"><i class="bx bx-grip-vertical"></i></span>
      <span class="queue-item-text" title="${esc(t.text)}" ondblclick="_queueEditTaskText(this,'${t.id}')">${esc(t.text)}</span>
      ${modeSelect}${modelSelect}
      <button class="queue-item-action" onclick="_queueEditTaskText(this.parentElement.querySelector('.queue-item-text'),'${t.id}')" title="Edit"><i class="bx bx-edit-alt"></i></button>
      <button class="queue-item-action" onclick="_queueSendNow('${t.id}')" title="Send now"><i class="bx bx-right-arrow-alt"></i></button>
      <button class="queue-item-remove" onclick="_queueRemoveTask('${t.id}')" title="Remove"><i class="bx bx-x"></i></button>
    </div>`;
  }).join('');
  container.innerHTML = `<div class="queue-panel">
    <div class="queue-header">
      <i class="bx bx-list-ol"></i> Queued Tasks <span class="queue-badge-count">${_queuedTasks.length}</span>
      <button class="queue-clear-btn" onclick="_queueClearAll()">Clear all</button>
    </div>
    <div class="queue-list">${items}</div>
  </div>`;
  _queuedTasks.forEach((t, i) => {
    const row = container.querySelectorAll('.queue-item')[i];
    if (!row) return;
    const selects = row.querySelectorAll('select');
    if (selects[0]) selects[0].value = t.mode || selectedMode;
    if (selects[1]) {
      const mval = t.model || selectedModel;
      const opts = Array.from(selects[1].options).map(o => o.value);
      if (opts.includes(mval)) {
        selects[1].value = mval;
      } else {
        const suffix = opts.find(o => mval.endsWith(o));
        selects[1].value = suffix || 'auto';
      }
    }
  });
}

async function _queueUpdateTask(taskId, updates) {
  if (!activeSessionId) return;
  try {
    await fetch(`/api/session/${activeSessionId}/queue`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({action:'update', task_id: taskId, ...updates})
    });
  } catch(e) { console.warn('Queue update failed:', e); }
}

async function _queueRemoveTask(taskId) {
  if (!activeSessionId) return;
  try {
    await fetch(`/api/session/${activeSessionId}/queue`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({action:'remove', task_id: taskId})
    });
  } catch(e) { console.warn('Queue remove failed:', e); }
}

async function _queueClearAll() {
  if (!activeSessionId) return;
  try {
    await fetch(`/api/session/${activeSessionId}/queue`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({action:'clear'})
    });
  } catch(e) { console.warn('Queue clear failed:', e); }
}

function _queueEditTaskText(spanEl, taskId) {
  if (spanEl.querySelector('input')) return;
  const oldText = spanEl.textContent;
  const input = document.createElement('input');
  input.type = 'text';
  input.value = oldText;
  input.className = 'queue-edit-input';
  input.style.cssText = 'width:100%;background:var(--bg);border:1px solid var(--accent);border-radius:4px;color:var(--text);font-size:12px;padding:2px 6px;font-family:var(--font);outline:none;';
  spanEl.textContent = '';
  spanEl.appendChild(input);
  input.focus();
  input.select();

  const commit = async () => {
    const newText = input.value.trim();
    spanEl.textContent = newText || oldText;
    if (newText && newText !== oldText) {
      await _queueUpdateTask(taskId, {text: newText});
    }
  };
  input.addEventListener('blur', commit);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); input.blur(); }
    if (e.key === 'Escape') { spanEl.textContent = oldText; }
  });
}

async function _queueSendNow(taskId) {
  if (!activeSessionId) return;
  try {
    await fetch(`/api/session/${activeSessionId}/queue`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({action:'reorder', task_id: taskId, index: 0})
    });
  } catch(e) { console.warn('Queue send-now failed:', e); }
}

let _qDragId = null;
function _qDragStart(e) { _qDragId = e.currentTarget.dataset.taskId; e.dataTransfer.effectAllowed = 'move'; }
function _qDragOver(e) { e.preventDefault(); e.currentTarget.classList.add('drag-over'); }
function _qDragLeave(e) { e.currentTarget.classList.remove('drag-over'); }
async function _qDrop(e) {
  e.preventDefault();
  e.currentTarget.classList.remove('drag-over');
  const targetIdx = parseInt(e.currentTarget.dataset.idx);
  if (!_qDragId || !activeSessionId) return;
  try {
    await fetch(`/api/session/${activeSessionId}/queue`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({action:'reorder', task_id: _qDragId, index: targetIdx})
    });
  } catch(e) { console.warn('Queue reorder failed:', e); }
  _qDragId = null;
}

function _updateFloatPanel() {
  const panel = $('float-actions');
  const stopBtn = $('btn-stop');
  const scrollBtn = $('btn-scroll-bottom');
  const chat = $('chat-area');
  const atBottom = chat ? (chat.scrollHeight - chat.scrollTop - chat.clientHeight < 80) : true;

  stopBtn.style.display = taskRunning ? '' : 'none';
  scrollBtn.style.display = atBottom ? 'none' : '';

  const anyVisible = taskRunning || !atBottom;
  panel.classList.toggle('visible', anyVisible);
}

function setStopMode(on) {
  taskRunning = on;
  _updateFloatPanel();
  _updateQueueBadge();
}

async function cancelTask() {
  try {
    await fetch(`/api/session/${activeSessionId}/cancel`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
  } catch (e) { console.warn('Cancel failed:', e); }
}

async function sendMessage() {
  const input = $('input');
  const text = input.value.trim();
  if (!text) return;

  if (taskRunning && activeSessionId) {
    input.value = '';
    input.style.height = 'auto';
    _autoResizeInput();
    const payload = { text, mode: selectedMode, model: selectedModel, turn_limit: selectedTurnLimit };
    fetch(`/api/session/${activeSessionId}/send`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload),
    }).catch(e => console.warn('Queue send failed:', e));
    return;
  }

  const welcome = $('welcome');
  if (welcome) welcome.remove();

  if (!activeSessionId) {
    await createNewSession();
  }

  sending = true;
  input.value = '';
  input.style.height = 'auto';
  input.placeholder = _('Type a message. Ctrl+Enter to send.');
  setStopMode(true);
  engine._localUserPending = true;
  engine._taskStartTime = Date.now();
  engine.enqueueEvent({ type: 'user', prompt: text });

  engine.showPendingModelBanner(selectedModel);
  _startConnectionWatchdog();

  try {
    const payload = { text, mode: selectedMode, model: selectedModel, turn_limit: selectedTurnLimit };
    const resp = await fetch(`/api/session/${activeSessionId}/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!data.ok) {
      console.error('Send failed:', data.error);
      _clearConnectionWatchdog();
      engine._clearPendingModelBanner();
      setStopMode(false);
    }
  } catch (err) {
    console.error('Send error:', err);
    _clearConnectionWatchdog();
    engine._clearPendingModelBanner();
    setStopMode(false);
  }
}
