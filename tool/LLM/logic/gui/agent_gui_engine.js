/**
 * Agent GUI Rendering Engine
 *
 * Protocol-driven rendering engine for LLM agent UIs.
 * Extracted as a reusable module so OPENCLAW and other tools
 * can embed the same Cursor-inspired UI.
 *
 * Usage:
 *   const engine = new AgentGUIEngine({ chatArea, todoList, panels });
 *   engine.registerBlock('memory', renderMemoryBlock);
 *   engine.loadTheme({ accent: '#e63946' });
 *   engine.processEvent({ type: 'text', tokens: 'Hello world' });
 *   engine.connectSSE('/api/events');
 */

const CHECK_SVG = '<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0a8 8 0 100 16A8 8 0 008 0zm3.5 6l-4 4-1 0-2-2 1-1 1.5 1.5L10.5 5l1 1z"/></svg>';
const FAIL_SVG = '<svg width="14" height="14" viewBox="0 0 24 24" fill="var(--red)"><path d="M12 2C6.47 2 2 6.47 2 12s4.47 10 10 10 10-4.47 10-10S17.53 2 12 2zm4.3 12.89L14.89 16.3 12 13.41 9.11 16.3 7.7 14.89 10.59 12 7.7 9.11 9.11 7.7 12 10.59 14.89 7.7 16.3 9.11 13.41 12 16.3 14.89z"/></svg>';

const SANDBOX_POLICIES = [
  { id: 'auto_run', label: 'Auto-run Mode', icon: 'bx-play-circle' },
  { id: 'ask', label: 'Ask Every Time', icon: 'bx-question-mark' },
  { id: 'sandbox', label: 'Run in Sandbox', icon: 'bx-box' },
  { id: 'run_all', label: 'Run Everything', icon: 'bx-check-double' },
];

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function md(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code style="background:var(--surface-3);padding:1px 5px;border-radius:3px;font-family:var(--mono);font-size:12px">$1</code>')
    .replace(/\n/g, '<br>');
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

function fileExtIcon(filename) {
  const ext = (filename || '').split('.').pop().toLowerCase();
  const map = {
    js: 'bxl-javascript', ts: 'bxl-typescript', jsx: 'bxl-react', tsx: 'bxl-react',
    py: 'bxl-python', html: 'bxl-html5', css: 'bxl-css3', scss: 'bxl-sass',
    json: 'bx-code-curly', md: 'bx-file', yaml: 'bx-file', yml: 'bx-file',
    sh: 'bx-terminal', bash: 'bx-terminal', go: 'bxl-go-lang', rs: 'bx-file',
    java: 'bxl-java', rb: 'bx-diamond', php: 'bxl-php', c: 'bx-file',
    cpp: 'bx-file', h: 'bx-file', sql: 'bx-data', vue: 'bxl-vuejs',
    svelte: 'bx-file', toml: 'bx-file', xml: 'bx-code', svg: 'bx-image',
  };
  return map[ext] || 'bx-code-alt';
}

function stripDiffPrefix(line) {
  return line.replace(/^[+\- ]\s*\d+\s*\|\s?/, '');
}

function renderDiffOutput(raw) {
  const lines = raw.split('\n');
  let html = '';
  let contextBuf = [];
  let addCount = 0, removeCount = 0;
  const CONTEXT_LIMIT = 3;

  function flushContext() {
    if (contextBuf.length <= CONTEXT_LIMIT * 2) {
      contextBuf.forEach(l => { html += '<div class="diff-line context">' + esc(l) + '</div>'; });
    } else {
      contextBuf.slice(0, CONTEXT_LIMIT).forEach(l => { html += '<div class="diff-line context">' + esc(l) + '</div>'; });
      const hidden = contextBuf.length - CONTEXT_LIMIT * 2;
      html += '<div class="diff-hidden" onclick="this.style.display=\'none\';this.nextElementSibling.style.display=\'block\'">' + hidden + ' hidden lines</div>';
      html += '<div style="display:none">';
      contextBuf.slice(CONTEXT_LIMIT, contextBuf.length - CONTEXT_LIMIT).forEach(l => { html += '<div class="diff-line context">' + esc(l) + '</div>'; });
      html += '</div>';
      contextBuf.slice(-CONTEXT_LIMIT).forEach(l => { html += '<div class="diff-line context">' + esc(l) + '</div>'; });
    }
    contextBuf = [];
  }

  for (const line of lines) {
    if (line.startsWith('+')) {
      if (contextBuf.length) flushContext();
      addCount++;
      html += '<div class="diff-line added">' + esc(stripDiffPrefix(line)) + '</div>';
    } else if (line.startsWith('-')) {
      if (contextBuf.length) flushContext();
      removeCount++;
      html += '<div class="diff-line removed">' + esc(stripDiffPrefix(line)) + '</div>';
    } else {
      contextBuf.push(stripDiffPrefix(line));
    }
  }
  if (contextBuf.length) flushContext();
  return { html, addCount, removeCount };
}

class AgentGUIEngine {
  constructor({ chatArea, todoListEl, execListEl, callListEl, execPanel, callPanel, todoPanel, sessionListEl }) {
    this.chatArea = chatArea;
    this.todoListEl = todoListEl;
    this.execListEl = execListEl;
    this.callListEl = callListEl;
    this.execPanel = execPanel;
    this.callPanel = callPanel;
    this.todoPanel = todoPanel;
    this.sessionListEl = sessionListEl;

    this.todoItems = {};
    this.execTrackers = {};
    this.callTrackers = {};
    this.blockRegistry = {};
    this.lastToolEl = null;
    this.toolIdx = 0;

    this.sessions = {};
    this.activeSessionId = null;
    this._onSessionChange = null;

    this._eventSource = null;
    this._scrollBtn = null;
    this._eventQueue = [];
    this._processing = false;
    this._sandboxPolicy = 'auto_run';

    this._registerDefaults();
    this._initScrollToBottom();
  }

  /* ── Block Registry ── */

  registerBlock(type, renderFn) {
    this.blockRegistry[type] = renderFn;
  }

  _registerDefaults() {
    this.registerBlock('user', (evt) => this._renderUser(evt));
    this.registerBlock('thinking', (evt) => this._renderThinking(evt));
    this.registerBlock('text', (evt) => this._renderText(evt));
    this.registerBlock('tool', (evt) => this._renderTool(evt));
    this.registerBlock('tool_result', (evt) => this._renderToolResult(evt));
    this.registerBlock('todo', (evt) => this._renderTodoInit(evt));
    this.registerBlock('todo_update', (evt) => this._updateTodo(evt));
    this.registerBlock('todo_delete', (evt) => this._deleteTodo(evt));
    this.registerBlock('experience', (evt) => this._renderExperience(evt));
    this.registerBlock('complete', (evt) => this._renderComplete(evt));
    this.registerBlock('llm_request', (evt) => this._renderLLMRequest(evt));
    this.registerBlock('llm_response_start', (evt) => this._renderLLMResponseStart(evt));
    this.registerBlock('llm_response_end', (evt) => this._renderLLMResponseEnd(evt));
    this.registerBlock('ask_user', (evt) => this._renderAskUser(evt));
  }

  /* ── Debug Mode ── */

  setDebugMode(enabled, createDebugBlockFn) {
    this._debugMode = enabled;
    this._createDebugBlock = createDebugBlockFn || null;
  }

  /* ── Process a single protocol event ── */

  async processEvent(evt) {
    const handler = this.blockRegistry[evt.type];
    if (handler) {
      if (this._debugMode && this._createDebugBlock) {
        const debugEl = this._createDebugBlock(evt);
        if (debugEl) this.chatArea.appendChild(debugEl);
      }
      await handler(evt);
      this._appendSpacer();
    }
  }

  /**
   * Enqueue an event for sequential processing.
   * Events are guaranteed to execute one at a time, in order.
   */
  enqueueEvent(evt) {
    this._eventQueue.push(evt);
    if (!this._processing) this._drainQueue();
  }

  async _drainQueue() {
    this._processing = true;
    try {
      while (this._eventQueue.length > 0) {
        const evt = this._eventQueue.shift();
        await this.processEvent(evt);
      }
    } finally {
      this._processing = false;
      if (this._eventQueue.length > 0) this._drainQueue();
    }
  }

  /* ── Process a batch of events (demo mode) ── */

  async runDemo(events, callbacks = {}) {
    for (const evt of events) {
      await this.processEvent(evt);
      if (callbacks.onEvent) callbacks.onEvent(evt);
    }
    if (callbacks.onComplete) callbacks.onComplete();
  }

  /* ── SSE Connection for real-time streaming ── */

  connectSSE(url) {
    if (this._eventSource) this._eventSource.close();
    this._eventSource = new EventSource(url);
    this._eventSource.onmessage = (e) => {
      try {
        const evt = JSON.parse(e.data);
        this.enqueueEvent(evt);
      } catch (err) {
        console.warn('SSE parse error:', err);
      }
    };
    this._eventSource.onerror = () => {
      console.warn('SSE connection lost, will retry...');
    };
  }

  disconnectSSE() {
    if (this._eventSource) {
      this._eventSource.close();
      this._eventSource = null;
    }
  }

  /* ── Theme Override ── */

  loadTheme(overrides) {
    const root = document.documentElement;
    for (const [key, value] of Object.entries(overrides)) {
      root.style.setProperty('--' + key, value);
    }
  }

  /* ── DOM Helpers ── */

  _appendEl(tag, cls, html, parent) {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (html) el.innerHTML = html;
    (parent || this.chatArea).appendChild(el);
    this._scrollEnd();
    return el;
  }

  _appendAnimated(tag, cls, html, parent) {
    const el = this._appendEl(tag, (cls || '') + ' block-enter', html, parent);
    requestAnimationFrame(() => requestAnimationFrame(() => el.classList.remove('block-enter')));
    return el;
  }

  _appendSpacer() {
    // No-op: turn-spacer removed per design
  }

  _isNearBottom() {
    const el = this.chatArea;
    return el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  }

  _scrollEnd() {
    if (this._isNearBottom()) {
      requestAnimationFrame(() => { this.chatArea.scrollTop = this.chatArea.scrollHeight; });
    }
  }

  /* ── Scroll-to-Bottom Button ── */

  _initScrollToBottom() {
    if (!this.chatArea) return;
    const btn = document.createElement('button');
    btn.className = 'scroll-to-bottom';
    btn.innerHTML = '<i class="bx bx-chevron-down"></i>';
    btn.title = 'Scroll to bottom';
    btn.onclick = () => {
      this.chatArea.scrollTo({ top: this.chatArea.scrollHeight, behavior: 'smooth' });
    };
    this.chatArea.parentElement.style.position = 'relative';
    this.chatArea.parentElement.appendChild(btn);
    this._scrollBtn = btn;

    this.chatArea.addEventListener('scroll', () => {
      if (this._scrollBtn) {
        this._scrollBtn.classList.toggle('visible', !this._isNearBottom());
      }
    });
  }

  /* ── Sandbox Policy ── */

  getSandboxPolicy() { return this._sandboxPolicy; }

  setSandboxPolicy(policyId) {
    this._sandboxPolicy = policyId;
    const label = document.querySelector('.sandbox-policy-label');
    const pol = SANDBOX_POLICIES.find(p => p.id === policyId);
    if (label && pol) label.textContent = pol.label;
  }

  /**
   * Create a sandbox policy selector dropdown.
   * Can be mounted in the header, status bar, or exec block.
   */
  createPolicySelector(container) {
    const wrapper = document.createElement('div');
    wrapper.className = 'sandbox-policy-selector';

    const current = SANDBOX_POLICIES.find(p => p.id === this._sandboxPolicy) || SANDBOX_POLICIES[0];
    wrapper.innerHTML =
      '<button class="sandbox-policy-btn" title="Execution policy">'
      + '<i class="bx bx-shield-quarter" style="font-size:14px;margin-right:4px"></i>'
      + '<span class="sandbox-policy-label">' + current.label + '</span>'
      + '<i class="bx bx-chevron-down" style="font-size:12px;margin-left:4px;opacity:0.5"></i>'
      + '</button>'
      + '<div class="sandbox-policy-menu">'
      + SANDBOX_POLICIES.map(p =>
          '<div class="sandbox-policy-option" data-policy="' + p.id + '">'
          + '<i class="bx ' + p.icon + '"></i>'
          + '<span>' + p.label + '</span>'
          + (p.id === this._sandboxPolicy ? '<i class="bx bx-check" style="margin-left:auto;color:var(--accent)"></i>' : '')
          + '</div>'
        ).join('')
      + '</div>';

    const btn = wrapper.querySelector('.sandbox-policy-btn');
    const menu = wrapper.querySelector('.sandbox-policy-menu');

    btn.onclick = (e) => {
      e.stopPropagation();
      menu.classList.toggle('visible');
    };

    wrapper.querySelectorAll('.sandbox-policy-option').forEach(opt => {
      opt.onclick = (e) => {
        e.stopPropagation();
        const pid = opt.dataset.policy;
        this.setSandboxPolicy(pid);
        menu.classList.remove('visible');
        wrapper.querySelectorAll('.bx-check').forEach(c => c.remove());
        opt.insertAdjacentHTML('beforeend', '<i class="bx bx-check" style="margin-left:auto;color:var(--accent)"></i>');
        wrapper.querySelector('.sandbox-policy-label').textContent =
          SANDBOX_POLICIES.find(p => p.id === pid).label;
      };
    });

    document.addEventListener('click', () => menu.classList.remove('visible'));

    container.appendChild(wrapper);
    return wrapper;
  }

  /* ── Session Management ── */

  onSessionChange(cb) { this._onSessionChange = cb; }

  addSession(id, title, status) {
    this.sessions[id] = { id, title: title || 'New Task', status: status || 'idle', createdAt: Date.now() };
    if (!this.activeSessionId) this.activeSessionId = id;
    this._refreshSessions();
    return this.sessions[id];
  }

  renameSession(id, newTitle) {
    if (!this.sessions[id]) return;
    this.sessions[id].title = newTitle;
    this._refreshSessions();
    if (this._onSessionChange) this._onSessionChange('rename', this.sessions[id]);
  }

  deleteSession(id) {
    if (!this.sessions[id]) return;
    delete this.sessions[id];
    if (this.activeSessionId === id) {
      const remaining = Object.keys(this.sessions);
      this.activeSessionId = remaining.length ? remaining[remaining.length - 1] : null;
    }
    this._refreshSessions();
    if (this._onSessionChange) this._onSessionChange('delete', { id });
  }

  setSessionStatus(id, status) {
    if (!this.sessions[id]) return;
    this.sessions[id].status = status;
    this._refreshSessions();
  }

  setActiveSession(id) {
    if (!this.sessions[id]) return;
    this.activeSessionId = id;
    this._refreshSessions();
    if (this._onSessionChange) this._onSessionChange('activate', this.sessions[id]);
  }

  getSession(id) { return this.sessions[id] || null; }
  listSessions() { return Object.values(this.sessions); }

  _refreshSessions() {
    if (!this.sessionListEl) return;
    this.sessionListEl.innerHTML = '';
    const sorted = Object.values(this.sessions).sort((a, b) => b.createdAt - a.createdAt);
    sorted.forEach(s => {
      const div = document.createElement('div');
      div.className = 'session-item' + (s.id === this.activeSessionId ? ' active' : '');
      div.dataset.sessionId = s.id;

      let dotIcon;
      if (s.status === 'running') {
        dotIcon = '<div class="spinner spinner-sm" style="border-top-color:var(--green)"></div>';
      } else if (s.status === 'done') {
        dotIcon = '<i class="bx bxs-check-circle"></i>';
      } else {
        dotIcon = '<i class="bx bx-circle"></i>';
      }

      div.innerHTML =
        '<div class="session-dot ' + esc(s.status) + '">' + dotIcon + '</div>'
        + '<div class="session-title-text" data-sid="' + esc(s.id) + '">' + esc(s.title) + '</div>'
        + '<div class="session-actions">'
        + '<button class="session-act-btn" title="Rename" data-action="rename"><i class="bx bx-pencil"></i></button>'
        + '<button class="session-act-btn danger" title="Delete" data-action="delete"><i class="bx bx-trash"></i></button>'
        + '</div>';

      div.querySelector('[data-action="rename"]').onclick = (e) => {
        e.stopPropagation();
        this._startRename(s.id);
      };
      div.querySelector('[data-action="delete"]').onclick = (e) => {
        e.stopPropagation();
        this._confirmDelete(s.id, s.title);
      };
      div.onclick = () => this.setActiveSession(s.id);

      this.sessionListEl.appendChild(div);
    });
  }

  _startRename(id) {
    const titleEl = this.sessionListEl.querySelector('[data-sid="' + id + '"]');
    if (!titleEl) return;
    const current = this.sessions[id].title;
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'session-rename-input';
    input.value = current;
    titleEl.replaceWith(input);
    input.focus();
    input.select();

    const commit = () => {
      const val = input.value.trim() || current;
      this.renameSession(id, val);
    };
    input.onblur = commit;
    input.onkeydown = (e) => {
      if (e.key === 'Enter') { e.preventDefault(); commit(); }
      if (e.key === 'Escape') { e.preventDefault(); this._refreshSessions(); }
    };
  }

  _confirmDelete(id, title) {
    const dialog = document.createElement('div');
    dialog.className = 'session-delete-dialog';
    dialog.innerHTML =
      '<div class="session-delete-box">'
      + '<div class="session-delete-title">Delete session?</div>'
      + '<div class="session-delete-msg">This will permanently remove <strong>' + esc(title) + '</strong>.</div>'
      + '<div class="session-delete-btns">'
      + '<button class="sdb-cancel">Cancel</button>'
      + '<button class="sdb-confirm">Delete</button>'
      + '</div></div>';
    document.body.appendChild(dialog);

    dialog.querySelector('.sdb-cancel').onclick = () => dialog.remove();
    dialog.querySelector('.sdb-confirm').onclick = () => {
      this.deleteSession(id);
      dialog.remove();
    };
    dialog.onclick = (e) => { if (e.target === dialog) dialog.remove(); };
  }

  /* ── Block Renderers ── */

  _renderUser(evt) {
    const content = evt.prompt || evt.text || '';
    this._appendAnimated('div', 'msg-user', esc(content));
    return sleep(400);
  }

  async _renderThinking(evt) {
    const text = (typeof evt.tokens === 'string') ? evt.tokens : '';
    const trivial = /^(Processing|Thinking|Working|Analyzing)[\s.]*$/i.test(text.trim())
                    || text.trim().length < 30;
    if (trivial) return;

    const el = this._appendAnimated('div', 'tool-call expanded',
      '<div class="tool-call-header" onclick="this.parentElement.classList.toggle(\'expanded\')">'
      + '<div class="tool-call-chevron"><i class="bx bx-chevron-right"></i></div>'
      + '<div class="tool-icon think">?</div>'
      + '<span class="tool-desc">Thinking</span>'
      + '<div class="tool-status running" data-tc="status"><div class="spinner spinner-sm think-spinner"></div></div>'
      + '</div>'
      + '<div class="tool-call-body">'
      + '<div class="think-body-content"><span class="think-content"></span><span class="think-cursor"></span></div>'
      + '</div>');

    const content = el.querySelector('.think-content');
    const cursor = el.querySelector('.think-cursor');

    let buf = '';
    for (const ch of text) {
      buf += ch;
      content.textContent = buf;
      this._scrollEnd();
      await sleep(8);
    }

    cursor.remove();
    const s = el.querySelector('[data-tc=status]');
    s.className = 'tool-status success';
    s.innerHTML = CHECK_SVG;
    el.classList.remove('expanded');
    await sleep(200);
  }

  async _renderText(evt) {
    const grp = this._appendAnimated('div', 'msg-group');
    const el = this._appendEl('div', 'msg-text', '', grp);
    await this._streamText(el, evt.tokens, 10);
    await sleep(200);
  }

  async _streamText(el, tokens, delay) {
    let buf = '';
    for (const ch of tokens) {
      buf += ch;
      el.innerHTML = md(buf);
      this._scrollEnd();
      await sleep(delay);
    }
  }

  _renderTool(evt) {
    this.toolIdx++;
    const tid = 'tool_' + this.toolIdx;
    this.lastToolEl = this._makeToolCall(evt.name, evt.desc, evt.cmd, evt.file);
    this.lastToolEl._trackerId = tid;

    if (evt.name === 'exec') {
      this._addExecTracker(tid, evt.cmd || evt.desc);
    } else if (evt.name !== 'edit') {
      this._addCallTracker(tid, evt.desc);
    }
    return sleep(800);
  }

  _renderToolResult(evt) {
    if (this.lastToolEl) {
      this._finishToolCall(this.lastToolEl, evt.ok, evt.output);
      const tid = this.lastToolEl._trackerId;
      if (this.lastToolEl.dataset.toolType !== 'edit' && tid) {
        if (this.execTrackers[tid]) this._finishExecTracker(tid, evt.ok);
        if (this.callTrackers[tid]) this._finishCallTracker(tid, evt.ok);
      }
      this.lastToolEl = null;
    }
    return sleep(300);
  }

  _renderTodoInit(evt) {
    this.todoItems = {};
    evt.items.forEach(i => { this.todoItems[i.id] = i; });
    if (this.todoPanel) this.todoPanel.style.display = '';
    this._refreshTodo();
    return sleep(400);
  }

  _updateTodo(evt) {
    if (this.todoItems[evt.id]) this.todoItems[evt.id].status = evt.status;
    this._refreshTodo();
    return sleep(200);
  }

  _deleteTodo(evt) {
    delete this.todoItems[evt.id];
    this._refreshTodo();
    return sleep(150);
  }

  _renderExperience(evt) {
    this._appendAnimated('div', 'experience-block', '<span>' + esc(evt.lesson) + '</span>');
    return sleep(500);
  }

  async _renderComplete(evt) {
    await sleep(300);
    this._appendAnimated('div', 'task-complete', CHECK_SVG + ' Task completed');
  }

  /* ── LLM API Events ── */

  _renderLLMRequest(evt) {
    const provider = evt.provider || 'LLM';
    const round = evt.round || 1;
    this._currentProvider = provider;
    this._currentRound = round;
    this._llmRequestEl = this._createModelInfoEl(provider, round);
    this.chatArea.appendChild(this._llmRequestEl);
    return sleep(100);
  }

  _renderLLMResponseStart(evt) {
    if (this._llmRequestEl) {
      const spinner = this._llmRequestEl.querySelector('.model-spinner');
      if (spinner) spinner.style.display = '';
      const latency = this._llmRequestEl.querySelector('.model-latency');
      if (latency) latency.textContent = '';
    }
    return sleep(50);
  }

  _renderLLMResponseEnd(evt) {
    if (this._llmRequestEl) {
      const spinner = this._llmRequestEl.querySelector('.model-spinner');
      if (spinner) spinner.style.display = 'none';

      const parts = [];
      const usage = evt.usage || {};
      const totalTokens = (usage.prompt_tokens || 0) + (usage.completion_tokens || 0);
      if (totalTokens > 0) {
        parts.push(totalTokens + ' tokens');
      }
      if (usage.cost != null) {
        const currency = this._costCurrency || '$';
        parts.push(currency + usage.cost.toFixed(4));
      } else if (totalTokens > 0) {
        parts.push('$0.00');
      }
      if (evt.latency_s) parts.push(evt.latency_s + 's');

      const latency = this._llmRequestEl.querySelector('.model-latency');
      if (latency) latency.textContent = parts.join(' · ') || (evt.latency_s ? evt.latency_s + 's' : '');

      this._lastLLMResponseEnd = evt;
      this._llmRequestEl = null;
    }
    return sleep(100);
  }

  setCostCurrency(symbol) {
    this._costCurrency = symbol;
  }

  _createModelInfoEl(provider, round) {
    const logos = typeof MODEL_LOGOS !== 'undefined' ? MODEL_LOGOS : {};
    const names = typeof MODEL_DISPLAY_NAMES !== 'undefined' ? MODEL_DISPLAY_NAMES : {};
    const name = names[provider] || provider;
    const logo = logos[provider] || '';
    const div = document.createElement('div');
    div.className = 'model-info';
    let html = '';
    if (logo) html += '<img src="' + logo + '" alt="' + esc(name) + '">';
    html += '<span class="model-name">' + esc(name) + '</span>';
    if (round > 1) html += '<span class="model-sep">·</span><span class="model-round">round ' + round + '</span>';
    html += '<span class="model-sep">·</span><div class="spinner spinner-sm model-spinner"></div><span class="model-latency"></span>';
    div.innerHTML = html;
    return div;
  }

  _renderAskUser(evt) {
    const el = this._appendAnimated('div', 'ask-user-block',
      '<div class="ask-user-icon"><i class="bx bx-question-mark"></i></div>'
      + '<div class="ask-user-text">' + md(evt.question || 'Agent is asking for your input') + '</div>');
    return sleep(300);
  }

  /* ── Tool Call Block ── */

  _makeToolCall(name, desc, cmd, file) {
    const isEdit = name === 'edit';
    let headerContent;

    if (isEdit) {
      const fname = file || cmd || desc;
      const iconClass = fileExtIcon(fname);
      headerContent =
        '<div class="tool-call-chevron"><i class="bx bx-chevron-right"></i></div>'
        + '<div class="tool-icon edit"><i class="bx ' + iconClass + '" style="font-size:13px"></i></div>'
        + '<span class="tool-desc">' + esc(fname) + '</span>'
        + '<span class="diff-stats" data-tc="diffstats"></span>'
        + '<div class="tool-status running" data-tc="status"><div class="spinner spinner-sm"></div></div>';
    } else {
      const icons = { exec: '$', read: 'R', read_file: 'R', write_file: 'W', search: 'S', think: '?', todo: 'T', ask_user: '?' };
      let labelText;
      if (name === 'exec' && cmd) {
        const cmdNames = cmd.split(/\s*&&\s*|\s*;\s*|\s*\|\|\s*/).map(c => c.trim().split(/\s+/)[0]).join(', ');
        labelText = cmdNames;
      } else {
        labelText = name.toUpperCase();
      }
      headerContent =
        '<div class="tool-call-chevron"><i class="bx bx-chevron-right"></i></div>'
        + '<div class="tool-icon ' + name + '">' + (icons[name]||'?') + '</div>'
        + '<span class="tool-desc">' + esc(desc) + '</span>'
        + '<span class="tool-label">' + esc(labelText) + '</span>'
        + '<div class="tool-status running" data-tc="status"><div class="spinner spinner-sm"></div></div>';
    }

    const bodyContent = isEdit
      ? '<div class="tool-terminal" data-tc="output" style="background:transparent;max-height:400px"></div>'
      : '<div class="tool-terminal-cmd"><span class="prompt">$</span> ' + esc(cmd || desc) + '</div>'
        + '<div class="tool-terminal" data-tc="output"></div>';

    const actionsHtml = '<div class="tool-call-actions">'
      + '<button title="Copy" onclick="event.stopPropagation()"><i class="bx bx-copy"></i></button>'
      + '<button title="Rerun" onclick="event.stopPropagation()"><i class="bx bx-revision"></i></button>'
      + '</div>';

    const el = this._appendAnimated('div', 'tool-call',
      '<div class="tool-call-header" onclick="this.parentElement.classList.toggle(\'expanded\')">'
      + headerContent + actionsHtml + '</div>'
      + '<div class="tool-call-body">' + bodyContent + '</div>');

    if (isEdit) el.dataset.toolType = 'edit';
    return el;
  }

  _finishToolCall(el, ok, output) {
    const s = el.querySelector('[data-tc=status]');
    if (s) {
      s.className = 'tool-status ' + (ok ? 'success' : 'error');
      s.innerHTML = ok ? CHECK_SVG : FAIL_SVG;
    }
    if (output) {
      const out = el.querySelector('[data-tc=output]');
      if (out) {
        if (el.dataset.toolType === 'edit') {
          const diff = renderDiffOutput(output);
          out.innerHTML = '<div class="diff-view">' + diff.html + '</div>';
          const stats = el.querySelector('[data-tc=diffstats]');
          if (stats) {
            let parts = [];
            if (diff.addCount) parts.push('<span class="added-count">+' + diff.addCount + '</span>');
            if (diff.removeCount) parts.push('<span class="removed-count">-' + diff.removeCount + '</span>');
            stats.innerHTML = parts.join(' ');
          }
          el.classList.add('expanded');
        } else {
          out.textContent = output;
        }
      }
    }
  }

  /* ── TODO ── */

  _refreshTodo() {
    if (!this.todoListEl) return;
    this.todoListEl.innerHTML = '';
    const entries = Object.values(this.todoItems);
    if (!entries.length && this.todoPanel) { this.todoPanel.style.display = 'none'; return; }
    entries.forEach(item => {
      const li = document.createElement('li');
      li.className = 'todo-item ' + item.status;
      const self = this;
      li.innerHTML =
        '<div class="todo-check"></div>'
        + '<span class="todo-text">' + esc(item.text) + '</span>'
        + '<span class="todo-badge ' + item.status + '">' + item.status.replace('_', ' ') + '</span>'
        + '<button class="todo-delete" title="Remove"><i class="bx bx-x"></i></button>';
      li.querySelector('.todo-delete').onclick = () => { self._deleteTodo({ id: item.id }); };
      this.todoListEl.appendChild(li);
    });
  }

  /* ── Exec Tracker ── */

  _addExecTracker(id, label) {
    this.execTrackers[id] = { label, status: 'running', startTime: Date.now() };
    if (this.execPanel) this.execPanel.style.display = '';
    this._refreshExecTrackers();
  }

  _finishExecTracker(id, ok) {
    if (this.execTrackers[id]) this.execTrackers[id].status = ok ? 'done' : 'failed';
    this._refreshExecTrackers();
    setTimeout(() => {
      delete this.execTrackers[id];
      this._refreshExecTrackers();
      if (!Object.keys(this.execTrackers).length && this.execPanel) this.execPanel.style.display = 'none';
    }, 1500);
  }

  _refreshExecTrackers() {
    if (!this.execListEl) return;
    this.execListEl.innerHTML = '';
    Object.entries(this.execTrackers).forEach(([id, t]) => {
      const li = document.createElement('li');
      li.className = 'tracker-item ' + t.status;
      const icon = t.status === 'running'
        ? '<div class="spinner spinner-sm"></div>'
        : (t.status === 'done' ? CHECK_SVG : FAIL_SVG);
      const elapsed = t.status === 'running' ? '' : '<span class="tracker-time">' + Math.round((Date.now() - t.startTime)/1000) + 's</span>';
      li.innerHTML = '<span class="tracker-icon">' + icon + '</span>'
        + '<span class="tracker-label">' + esc(t.label) + '</span>' + elapsed;
      this.execListEl.appendChild(li);
    });
  }

  /* ── Call Tracker ── */

  _addCallTracker(id, label) {
    this.callTrackers[id] = { label, status: 'running', startTime: Date.now() };
    if (this.callPanel) this.callPanel.style.display = '';
    this._refreshCallTrackers();
  }

  _finishCallTracker(id, ok) {
    if (this.callTrackers[id]) this.callTrackers[id].status = ok ? 'done' : 'failed';
    this._refreshCallTrackers();
    setTimeout(() => {
      delete this.callTrackers[id];
      this._refreshCallTrackers();
      if (!Object.keys(this.callTrackers).length && this.callPanel) this.callPanel.style.display = 'none';
    }, 1500);
  }

  _refreshCallTrackers() {
    if (!this.callListEl) return;
    this.callListEl.innerHTML = '';
    Object.entries(this.callTrackers).forEach(([id, t]) => {
      const li = document.createElement('li');
      li.className = 'tracker-item ' + t.status;
      const icon = t.status === 'running'
        ? '<div class="spinner spinner-sm"></div>'
        : (t.status === 'done' ? CHECK_SVG : FAIL_SVG);
      const elapsed = t.status === 'running' ? '' : '<span class="tracker-time">' + Math.round((Date.now() - t.startTime)/1000) + 's</span>';
      li.innerHTML = '<span class="tracker-icon">' + icon + '</span>'
        + '<span class="tracker-label">' + esc(t.label) + '</span>' + elapsed;
      this.callListEl.appendChild(li);
    });
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { AgentGUIEngine, esc, md, sleep, CHECK_SVG, FAIL_SVG };
}
