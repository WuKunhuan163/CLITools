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

function escWbr(s) {
  return esc(s).replace(/([/._\-\\])/g, '$1<wbr>');
}

function md(text) {
  const codeBlocks = [];
  let s = text.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    const idx = codeBlocks.length;
    codeBlocks.push(`<pre class="md-codeblock"><code>${esc(code.replace(/\n$/, ''))}</code></pre>`);
    return `\x00CB${idx}\x00`;
  });

  const lines = s.split('\n');
  const out = [];
  let inList = false;

  for (const line of lines) {
    const h3 = line.match(/^### (.+)/);
    const h2 = line.match(/^## (.+)/);
    const h1 = line.match(/^# (.+)/);
    const li = line.match(/^[-*] (.+)/);

    if (line.trim() === '---' || line.trim() === '***' || line.trim() === '___') {
      if (inList) { out.push('</ul>'); inList = false; }
      out.push('<hr class="md-hr">');
    }
    else if (h1) { if (inList) { out.push('</ul>'); inList = false; } out.push(`<h3 class="md-h1">${inlineMd(h1[1])}</h3>`); }
    else if (h2) { if (inList) { out.push('</ul>'); inList = false; } out.push(`<h4 class="md-h2">${inlineMd(h2[1])}</h4>`); }
    else if (h3) { if (inList) { out.push('</ul>'); inList = false; } out.push(`<h5 class="md-h3">${inlineMd(h3[1])}</h5>`); }
    else if (li) { if (!inList) { out.push('<ul class="md-list">'); inList = true; } out.push(`<li>${inlineMd(li[1])}</li>`); }
    else { if (inList) { out.push('</ul>'); inList = false; } out.push(inlineMd(line) + '<br>'); }
  }
  if (inList) out.push('</ul>');

  let result = out.join('');
  result = result.replace(/\x00CB(\d+)\x00/g, (_, idx) => codeBlocks[+idx]);
  return result;
}

function inlineMd(text) {
  const inlineCode = [];
  let safe = text.replace(/`(.+?)`/g, (_, code) => {
    const idx = inlineCode.length;
    inlineCode.push(`<code class="md-inline-code">${esc(code)}</code>`);
    return `\x01IC${idx}\x01`;
  });
  safe = esc(safe);
  safe = safe
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>');
  safe = safe.replace(/\x01IC(\d+)\x01/g, (_, idx) => inlineCode[+idx]);
  return safe;
}

let _replayMode = false;
function sleep(ms) {
  if (_replayMode) return Promise.resolve();
  return new Promise(r => setTimeout(r, ms));
}

const _DEVICON_BASE = 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons';
const _DEVICON_MAP = {
  py: 'python/python-original', js: 'javascript/javascript-original',
  ts: 'typescript/typescript-original', jsx: 'react/react-original',
  tsx: 'react/react-original', html: 'html5/html5-original',
  css: 'css3/css3-original', scss: 'sass/sass-original',
  json: 'json/json-original', md: 'markdown/markdown-original',
  yaml: 'yaml/yaml-original', yml: 'yaml/yaml-original',
  sh: 'bash/bash-original', bash: 'bash/bash-original',
  go: 'go/go-original', rs: 'rust/rust-original',
  java: 'java/java-original', rb: 'ruby/ruby-original',
  php: 'php/php-original', c: 'c/c-original', cpp: 'cplusplus/cplusplus-original',
  h: 'c/c-original', sql: 'postgresql/postgresql-original',
  vue: 'vuejs/vuejs-original', svelte: 'svelte/svelte-original',
  xml: 'xml/xml-original', swift: 'swift/swift-original',
  kt: 'kotlin/kotlin-original', dart: 'dart/dart-original',
  r: 'r/r-original', lua: 'lua/lua-original',
};
const _BOXICON_FALLBACK = {
  toml: 'bx-file', svg: 'bx-image',
};
function fileExtIcon(filename) {
  const ext = (filename || '').split('.').pop().toLowerCase();
  if (_DEVICON_MAP[ext]) return `_devicon_:${_DEVICON_BASE}/${_DEVICON_MAP[ext]}.svg`;
  return _BOXICON_FALLBACK[ext] || 'bx-code-alt';
}
function renderFileIcon(filename) {
  const icon = fileExtIcon(filename);
  if (icon.startsWith('_devicon_:')) {
    const url = icon.slice('_devicon_:'.length);
    return '<img src="' + url + '" class="logo-adaptive" crossorigin="anonymous" style="width:14px;height:14px;vertical-align:middle;margin-right:2px;" alt="">';
  }
  return '<i class="bx ' + icon + '"></i>';
}

function stripDiffPrefix(line) {
  return line.replace(/^[+\-]\s*\d*\s*\|?\s?/, '').replace(/^\s*\d+\s*\|\s?/, '');
}

function _renderSearchOutput(raw) {
  if (!raw || raw === '(no matches)') return '<span style="color:var(--text-3);font-size:11px">(no matches)</span>';
  const lines = raw.split('\n').filter(l => l.trim());
  return lines.map(line => {
    const m = line.match(/^(\d+):(.*)$/);
    if (m) {
      return '<div style="font-family:var(--mono);font-size:11px;line-height:1.6;white-space:pre-wrap;word-break:break-word">'
        + '<span style="color:var(--accent);font-weight:600">' + esc(m[1]) + '</span>'
        + '<span style="color:var(--text-3)">:</span> '
        + '<span style="color:var(--text)">' + esc(m[2]) + '</span></div>';
    }
    const fm = line.match(/^(.+?):(\d+):(.*)$/);
    if (fm) {
      return '<div style="font-family:var(--mono);font-size:11px;line-height:1.6;white-space:pre-wrap;word-break:break-word">'
        + '<span style="color:var(--text-3)">' + esc(fm[1]) + '</span>'
        + '<span style="color:var(--text-3)">:</span>'
        + '<span style="color:var(--accent);font-weight:600">' + esc(fm[2]) + '</span>'
        + '<span style="color:var(--text-3)">:</span>'
        + '<span style="color:var(--text)">' + esc(fm[3]) + '</span></div>';
    }
    return '<div style="font-family:var(--mono);font-size:11px;color:var(--text-2)">' + esc(line) + '</div>';
  }).join('');
}

let _diffHunkId = 0;
function renderDiffOutput(raw, enableHunkActions) {
  const lines = raw.split('\n');
  let html = '';
  let hunkBuf = [];
  let addCount = 0, removeCount = 0;

  function flushHunk() {
    if (!hunkBuf.length) return;
    if (enableHunkActions) {
      const hid = 'dhunk-' + (++_diffHunkId);
      html += '<div class="diff-hunk" id="' + hid + '" data-removed="' + esc(hunkBuf.filter(l=>l.t==='-').map(l=>l.s).join('\n')) + '" data-added="' + esc(hunkBuf.filter(l=>l.t==='+').map(l=>l.s).join('\n')) + '">';
      html += '<div class="diff-hunk-actions">'
        + '<button class="diff-hunk-btn accept" title="Accept this change" onclick="window._diffHunkAction(this,\'accept\')"><i class="bx bx-check"></i></button>'
        + '<button class="diff-hunk-btn reject" title="Reject this change" onclick="window._diffHunkAction(this,\'reject\')"><i class="bx bx-x"></i></button>'
        + '</div>';
    }
    hunkBuf.forEach(h => {
      const cls = h.t === '+' ? 'added' : 'removed';
      html += '<div class="diff-line ' + cls + '"><span class="diff-ln diff-marker">' + h.t + '</span>' + esc(h.s) + '</div>';
    });
    if (enableHunkActions) html += '</div>';
    hunkBuf = [];
  }

  for (const line of lines) {
    const hideMatch = line.match(/^@@hide\s+(\d+)/);
    if (hideMatch) {
      flushHunk();
      const n = parseInt(hideMatch[1]);
      html += '<div class="diff-hidden-sep">' + n + ' hidden lines</div>';
    } else if (line.startsWith('+')) {
      addCount++;
      hunkBuf.push({ t: '+', s: line.slice(1) });
    } else if (line.startsWith('-')) {
      removeCount++;
      hunkBuf.push({ t: '-', s: line.slice(1) });
    } else {
      flushHunk();
      const ctxMatch = line.match(/^\s*(\d+)\|(.*)$/);
      if (ctxMatch) {
        const ln = ctxMatch[1];
        const content = ctxMatch[2];
        html += '<div class="diff-line context"><span class="diff-ln">' + ln + '</span>' + esc(content) + '</div>';
      } else {
        html += '<div class="diff-line context">' + esc(stripDiffPrefix(line)) + '</div>';
      }
    }
  }
  flushHunk();
  return { html, addCount, removeCount };
}

function _renderReadDisplay(raw) {
  const lines = raw.split('\n');
  let html = '';
  let inRead = false;
  let readCount = 0;
  for (const line of lines) {
    const hideMatch = line.match(/^@@hide\s+(\d+)/);
    if (hideMatch) {
      html += '<div class="diff-hidden-sep">' + hideMatch[1] + ' hidden lines</div>';
      continue;
    }
    if (line === '@@read') { inRead = true; continue; }
    if (line === '@@read_end') { inRead = false; continue; }
    const m = line.match(/^(\s*\d+)\|(.*)/);
    if (inRead) {
      readCount++;
      if (m) {
        html += '<div class="diff-line read-focus"><span class="read-lineno">' + m[1] + '</span>' + esc(m[2]) + '</div>';
      } else {
        html += '<div class="diff-line read-focus">' + esc(line) + '</div>';
      }
    } else {
      if (m) {
        html += '<div class="diff-line context"><span class="diff-ln">' + m[1] + '</span>' + esc(m[2]) + '</div>';
      } else if (line.trim()) {
        html += '<div class="diff-line context">' + esc(line) + '</div>';
      }
    }
  }
  return { html, readCount };
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
    this._modifiedFiles = [];
    this._lastToolEvt = null;

    this._taskFiles = {};
    this._taskActive = false;
    this._taskFileBarEl = null;

    this.sessions = {};
    this.activeSessionId = null;
    this._onSessionChange = null;

    this._eventSource = null;
    this._scrollBtn = null;
    this._eventQueue = [];
    this._processing = false;
    this._sandboxPolicy = 'auto_run';
    this._activeTextEl = null;
    this._activeTextGrp = null;
    this._activeTextBuf = '';
    this._activeThinkEl = null;
    this._activeThinkBlock = null;
    this._activeThinkBuf = '';
    this._textRafPending = false;
    this._thinkRafPending = false;
    this._roundHistory = [];
    this._maxRoundHistory = 16;
    this._maxContextTokens = 0;

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
    this.registerBlock('notice', (evt) => this._renderNotice(evt));
    this.registerBlock('system_notice', (evt) => this._renderNotice(evt));
    this.registerBlock('debug', (evt) => this._renderDebugNotice(evt));
    this.registerBlock('file_summary', (evt) => this._renderFileSummary(evt));
    this.registerBlock('tool_stream_start', (evt) => this._renderToolStreamStart(evt));
    this.registerBlock('tool_stream_delta', (evt) => this._renderToolStreamDelta(evt));
    this.registerBlock('tool_stream_end', (evt) => this._renderToolStreamEnd(evt));
    this.registerBlock('model_decision_start', (evt) => this._renderModelDecisionStart(evt));
    this.registerBlock('model_decision_end', (evt) => this._renderModelDecisionEnd(evt));
    this.registerBlock('model_decision_proposed', (evt) => this._renderModelDecisionProposed(evt));
    this.registerBlock('model_confirmed', (evt) => this._renderModelConfirmed(evt));
  }

  /* ── Replay / Debug Mode ── */

  setReplayMode(on) { _replayMode = !!on; }

  setDebugMode(enabled, createDebugBlockFn) {
    this._debugMode = enabled;
    this._createDebugBlock = createDebugBlockFn || null;
  }

  /* ── Process a single protocol event ── */

  async processEvent(evt) {
    try {
    const isStreamDelta = evt.type === 'tool_stream_delta';
    if (evt.type !== 'text' && !isStreamDelta) {
      this._clearActiveText();
    }
    if (this._createDebugBlock && !isStreamDelta) {
      const debugEl = this._createDebugBlock(evt);
      if (debugEl) this.chatArea.appendChild(debugEl);
    }
    const handler = this.blockRegistry[evt.type];
    if (handler) {
      await handler(evt);
      if (evt.type !== 'text' && !isStreamDelta) this._appendSpacer();
    }
    } catch (err) {
      console.error('[AgentGUIEngine] processEvent error:', err, 'evt:', evt);
    }
  }

  /**
   * Enqueue an event for sequential processing.
   * Events are guaranteed to execute one at a time, in order.
   */
  enqueueEvent(evt) {
    if (evt.type === 'text' && this._eventQueue.length > 0) {
      const last = this._eventQueue[this._eventQueue.length - 1];
      if (last.type === 'text') {
        last.tokens = (last.tokens || '') + (evt.tokens || '');
        return;
      }
    }
    if (evt.type === 'tool_stream_delta' && this._eventQueue.length > 0) {
      const last = this._eventQueue[this._eventQueue.length - 1];
      if (last.type === 'tool_stream_delta' && last.index === evt.index) {
        last.content = (last.content || '') + (evt.content || '');
        return;
      }
    }
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
    return el.scrollHeight - el.scrollTop - el.clientHeight < 120;
  }

  _scrollEnd() {
    if (this._userScrolledUp) return;
    if (this._isNearBottom() || this._forceScroll) {
      requestAnimationFrame(() => { this.chatArea.scrollTop = this.chatArea.scrollHeight; });
    }
  }

  _forceScrollToBottom() {
    this._userScrolledUp = false;
    this._forceScroll = true;
    requestAnimationFrame(() => {
      this.chatArea.scrollTop = this.chatArea.scrollHeight;
      this._forceScroll = false;
    });
  }

  /* ── Scroll-to-Bottom Button ── */

  _initScrollToBottom() {
    if (!this.chatArea) return;
    this._scrollBtn = null;
    this._userScrolledUp = false;
    this._forceScroll = false;
    let _lastScrollTop = this.chatArea.scrollTop;

    this.chatArea.addEventListener('scroll', () => {
      const cur = this.chatArea.scrollTop;
      if (cur < _lastScrollTop && !this._isNearBottom()) {
        this._userScrolledUp = true;
      }
      if (this._isNearBottom()) {
        this._userScrolledUp = false;
      }
      _lastScrollTop = cur;
      if (typeof _updateFloatPanel === 'function') _updateFloatPanel();
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

  addSession(id, title, status, mode) {
    this.sessions[id] = { id, title: title || 'New Task', status: status || 'idle', mode: mode || 'agent', createdAt: Date.now() };
    if (!this.activeSessionId) this.activeSessionId = id;
    this._refreshSessions();
    return this.sessions[id];
  }

  renameSession(id, newTitle, skipSync) {
    if (!this.sessions[id]) return;
    this.sessions[id].title = newTitle;
    this._refreshSessions();
    if (this._onSessionChange) this._onSessionChange('rename', this.sessions[id]);
    if (!skipSync) {
      fetch(`/api/session/${id}/rename`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({title: newTitle})
      }).catch(() => {});
    }
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

  setSessionStatus(id, status, reason) {
    if (!this.sessions[id]) return;
    this.sessions[id].status = status;
    if (status === 'running') {
      delete this.sessions[id].doneReason;
    } else if (reason) {
      this.sessions[id].doneReason = reason;
    }
    this._refreshSessions();
  }

  setActiveSession(id) {
    if (!this.sessions[id]) return;
    this.activeSessionId = id;
    this.resetSessionState();
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
        const r = s.doneReason || '';
        if (r === 'cancelled' || r === 'error') {
          dotIcon = '<i class="bx bx-x-circle"></i>';
        } else if (r === 'round_limit') {
          dotIcon = '<i class="bx bx-error-circle"></i>';
        } else {
          dotIcon = '<i class="bx bxs-check-circle"></i>';
        }
      } else {
        dotIcon = '<i class="bx bx-circle"></i>';
      }

      const dotCls = s.status + (s.status === 'done' && s.doneReason ? '-' + s.doneReason : '');
      div.innerHTML =
        '<div class="session-dot ' + esc(dotCls) + '">' + dotIcon + '</div>'
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
    if (!this._taskActive) {
      this._taskFiles = {};
      this._taskActive = true;
      this._removeTaskFileBar();
      const prev = this.chatArea.querySelector('.task-complete:last-of-type');
      if (prev) prev.remove();
    }
    this._appendAnimated('div', 'msg-user', esc(content));
    this._forceScrollToBottom();
    return sleep(400);
  }

  async _renderThinking(evt) {
    const text = (typeof evt.tokens === 'string') ? evt.tokens : '';
    if (!text) return;
    this._trackStreamingChars(text.length);

    if (this._activeThinkEl && this._activeThinkBlock && this._activeThinkBlock.parentNode === this.chatArea) {
      this._activeThinkBuf += text;
      if (!this._thinkRafPending) {
        this._thinkRafPending = true;
        requestAnimationFrame(() => {
          this._thinkRafPending = false;
          if (this._activeThinkEl) {
            this._activeThinkEl.textContent = this._activeThinkBuf;
            this._activeThinkBlock.classList.add('expanded');
            this._scrollEnd();
          }
        });
      }
      return;
    }

    const trivial = /^(Processing|Thinking|Working|Analyzing)[\s.]*$/i.test(text.trim())
                    || text.trim().length < 30;
    if (trivial && !this._activeThinkEl) return;

    const duration = evt.duration ? Math.round(evt.duration) + 's' : '';
    const el = this._appendAnimated('div', 'thought-block expanded',
      '<div class="thought-header" onclick="this.parentElement.classList.toggle(\'expanded\')">'
      + '<span class="thought-label">Thought</span>'
      + '<span class="thought-duration" data-tc="duration">' + (duration ? 'for ' + duration : '') + '</span>'
      + '<i class="bx bx-chevron-down thought-chevron"></i>'
      + '</div>'
      + '<div class="thought-body"><span class="think-content"></span></div>');

    const content = el.querySelector('.think-content');
    this._activeThinkBlock = el;
    this._activeThinkEl = content;
    this._activeThinkBuf = text;

    if (_replayMode) {
      content.textContent = text;
    } else {
      content.textContent = text;
      this._scrollEnd();
    }
    await sleep(200);
  }

  async _renderText(evt) {
    const tokens = evt.tokens || '';
    if (tokens.length > 0) this._trackStreamingChars(tokens.length);
    if (this._activeTextEl && this._activeTextGrp && this._activeTextGrp.parentNode === this.chatArea) {
      this._activeTextBuf += tokens;
      this._scheduleTextRender();
      return;
    }
    const grp = this._appendAnimated('div', 'msg-group');
    const el = this._appendEl('div', 'msg-text', '', grp);
    this._activeTextGrp = grp;
    this._activeTextEl = el;
    this._activeTextBuf = tokens;
    this._scheduleTextRender();
  }

  _scheduleTextRender() {
    if (this._textRafPending) return;
    this._textRafPending = true;
    requestAnimationFrame(() => {
      this._textRafPending = false;
      if (this._activeTextEl && this._activeTextBuf) {
        this._activeTextEl.innerHTML = md(this._activeTextBuf);
        this._scrollEnd();
      }
    });
  }

  _clearActiveText() {
    if (this._textRafPending && this._activeTextEl && this._activeTextBuf) {
      this._activeTextEl.innerHTML = md(this._activeTextBuf);
    }
    this._activeTextEl = null;
    this._activeTextGrp = null;
    this._activeTextBuf = '';
    this._textRafPending = false;
    if (this._thinkRafPending && this._activeThinkEl && this._activeThinkBuf) {
      this._activeThinkEl.textContent = this._activeThinkBuf;
    }
    if (this._activeThinkBlock) {
      this._activeThinkBlock.classList.remove('expanded');
    }
    this._activeThinkEl = null;
    this._activeThinkBlock = null;
    this._activeThinkBuf = '';
    this._thinkRafPending = false;
  }

  /* _streamText removed: real streaming uses RAF-batched rendering */

  _renderTool(evt) {
    this.toolIdx++;
    const tid = 'tool_' + this.toolIdx;

    if (this.lastToolEl && this.lastToolEl.querySelector('.tool-stream-content')) {
      this.lastToolEl._trackerId = tid;
      this._lastToolEvt = evt;
      this.lastToolEl.dataset.sid = this.activeSessionId || '';
      this.lastToolEl.dataset.round = this._currentRound || 0;
      this.lastToolEl.dataset.toolName = evt.name || '';
      this.lastToolEl.dataset.toolCmd = evt.cmd || '';
      const isEditType = evt.name === 'edit' || evt.name === 'edit_file' || evt.name === 'write_file';
      if (isEditType) {
        this.lastToolEl.dataset.toolType = evt.name === 'write_file' ? 'write' : 'edit';
      }
      const body = this.lastToolEl.querySelector('.tool-call-body');
      if (body && !body.querySelector('[data-tc=output]')) {
        const streamEl = this.lastToolEl.querySelector('.tool-stream-content');
        if (streamEl) streamEl.style.display = 'none';
        const outEl = document.createElement('div');
        outEl.className = 'tool-terminal';
        outEl.setAttribute('data-tc', 'output');
        outEl.style.background = 'transparent';
        outEl.style.maxHeight = '400px';
        body.appendChild(outEl);
      }
      if (isEditType) {
        const descEl = this.lastToolEl.querySelector('.tool-desc');
        const info = this._naturalToolDesc(evt.name, evt.desc, evt.cmd, evt.file);
        if (descEl) descEl.textContent = info.label || evt.desc || 'Applying...';
        if (!this.lastToolEl.querySelector('[data-tc=diffstats]')) {
          const hdr = this.lastToolEl.querySelector('.tool-call-header');
          if (hdr) {
            const statsSpan = document.createElement('span');
            statsSpan.className = 'diff-stats';
            statsSpan.setAttribute('data-tc', 'diffstats');
            hdr.insertBefore(statsSpan, hdr.querySelector('[data-tc=status]'));
          }
        }
      }
      return sleep(0);
    }

    this.lastToolEl = this._makeToolCall(evt.name, evt.desc, evt.cmd, evt.file);
    this.lastToolEl._trackerId = tid;
    this._lastToolEvt = evt;
    this.lastToolEl.dataset.sid = this.activeSessionId || '';
    this.lastToolEl.dataset.round = this._currentRound || 0;
    this.lastToolEl.dataset.toolName = evt.name || '';
    this.lastToolEl.dataset.toolCmd = evt.cmd || '';

    const fileLink = this.lastToolEl.querySelector('.tool-file-link');
    if (fileLink) {
      const sid = this.activeSessionId;
      const rd = this._currentRound;
      const op = fileLink.dataset.op;
      const rawPath = (evt.cmd || evt.file || '').replace(/^(edit|write|read)\s+/i, '');
      fileLink.addEventListener('click', (e) => {
        e.stopPropagation();
        if (sid && rd && rawPath) {
          const relPath = rawPath.replace(/^\/Applications\/AITerminalTools\//, '');
          window.open(`/session/${sid}/${op}/${rd}/${relPath}/0`, '_blank');
        }
      });
    }

    const isEditType = evt.name === 'edit' || evt.name === 'edit_file' || evt.name === 'write_file';
    if (evt.name === 'exec') {
      this._addExecTracker(tid, evt.cmd || evt.desc);
    } else if (!isEditType) {
      this._addCallTracker(tid, evt.desc);
    }
    return sleep(800);
  }

  _renderToolResult(evt) {
    if (this.lastToolEl) {
      this._finishToolCall(this.lastToolEl, evt.ok, evt.output, evt);
      const tid = this.lastToolEl._trackerId;
      const toolType = this.lastToolEl.dataset.toolType;
      if (toolType !== 'edit' && toolType !== 'write' && tid) {
        if (this.execTrackers[tid]) this._finishExecTracker(tid, evt.ok);
        if (this.callTrackers[tid]) this._finishCallTracker(tid, evt.ok);
      }
      if (this._lastToolEvt && evt.ok) {
        const te = this._lastToolEvt;
        const n = te.name;
        if (n === 'write_file' || n === 'edit_file' || n === 'edit') {
          const fname = te.file || te.cmd || te.desc || '';
          const cleanPath = fname.replace(/^(write|edit)\s+/, '');
          let added = 0, removed = 0;
          const statsEl = this.lastToolEl.querySelector('[data-tc=diffstats]');
          if (statsEl) {
            const ac = statsEl.querySelector('.added-count');
            const rc = statsEl.querySelector('.removed-count');
            if (ac) added = parseInt(ac.textContent.replace('+', ''), 10) || 0;
            if (rc) removed = parseInt(rc.textContent.replace('-', ''), 10) || 0;
          }
          this._modifiedFiles.push({ name: cleanPath.split('/').pop() || cleanPath, path: cleanPath, type: n === 'write_file' ? 'new' : 'edit', added, removed });
          const key = cleanPath;
          if (this._taskFiles[key]) {
            this._taskFiles[key].added += added;
            this._taskFiles[key].removed += removed;
          } else {
            this._taskFiles[key] = { name: cleanPath.split('/').pop() || cleanPath, path: cleanPath, type: n === 'write_file' ? 'new' : 'edit', added, removed };
          }
          this._updateTaskFileBar();
        }
      }
      this.lastToolEl = null;
      this._lastToolEvt = null;
    }
    return sleep(300);
  }

  /* ── Streaming Tool Blocks ── */

  _renderToolStreamStart(evt) {
    this._clearActiveText();
    const idx = evt.index || 0;
    const name = evt.name || 'tool';

    const isEdit = name === 'edit_file' || name === 'write_file' || name === 'edit';
    const isThink = name === 'think';

    let headerHtml, bodyClass;
    if (isEdit) {
      headerHtml =
        '<div class="tool-call-chevron"><i class="bx bx-chevron-right"></i></div>'
        + '<div class="tool-icon edit"><i class="bx bx-code-alt" style="font-size:13px"></i></div>'
        + '<span class="tool-desc">Writing...</span>'
        + '<div class="tool-status running" data-tc="status"><div class="spinner spinner-sm"></div></div>';
      bodyClass = 'streaming-edit';
    } else if (isThink) {
      headerHtml =
        '<div class="tool-call-chevron"><i class="bx bx-chevron-right"></i></div>'
        + '<i class="bx bx-brain tool-natural-icon"></i>'
        + '<span class="tool-desc">Thinking...</span>'
        + '<div class="tool-status running" data-tc="status"><div class="spinner spinner-sm"></div></div>';
      bodyClass = 'streaming-think';
    } else {
      headerHtml =
        '<div class="tool-call-chevron"><i class="bx bx-chevron-right"></i></div>'
        + '<i class="bx bx-code-alt tool-natural-icon"></i>'
        + '<span class="tool-desc">' + esc(name) + '...</span>'
        + '<div class="tool-status running" data-tc="status"><div class="spinner spinner-sm"></div></div>';
      bodyClass = 'streaming-generic';
    }

    const el = this._appendAnimated('div', 'tool-call expanded',
      '<div class="tool-call-header" onclick="this.parentElement.classList.toggle(\'expanded\')">'
      + headerHtml + '</div>'
      + '<div class="tool-call-body">'
      + '<pre class="tool-stream-content ' + bodyClass + '" data-tc="stream"></pre>'
      + '</div>');

    if (!this._streamingTools) this._streamingTools = {};
    this._streamingTools[idx] = {
      el: el,
      contentEl: el.querySelector('[data-tc=stream]'),
      buffer: '',
      name: name,
    };
    return sleep(0);
  }

  _renderToolStreamDelta(evt) {
    const idx = evt.index || 0;
    const st = this._streamingTools && this._streamingTools[idx];
    if (!st) return sleep(0);

    st.buffer += (evt.content || '');
    st._dirty = true;

    if (!st._rafPending) {
      st._rafPending = true;
      requestAnimationFrame(() => {
        st._rafPending = false;
        if (!st._dirty) return;
        st._dirty = false;
        const contentEl = st.contentEl;
        if (contentEl) {
          const isEdit = st.name === 'edit_file' || st.name === 'write_file' || st.name === 'edit';
          if (isEdit) {
            this._renderStreamingEdit(st, contentEl);
          } else if (st.name === 'think') {
            contentEl.textContent = this._extractThinkContent(st);
          } else {
            contentEl.textContent = st.buffer;
          }
          this._scrollEnd();
        }
      });
    }
    return sleep(0);
  }

  _renderStreamingEdit(st, contentEl) {
    if (!st._editParsed) {
      const pathM = st.buffer.match(/"path"\s*:\s*"([^"]*)"/);
      if (pathM && !st._editPath) {
        st._editPath = pathM[1];
        const descEl = st.el && st.el.querySelector('.tool-desc');
        if (descEl) descEl.textContent = 'Editing ' + st._editPath.split('/').pop() + '...';
      }
      const slM = st.buffer.match(/"start_line"\s*:\s*(\d+)/);
      const elM = st.buffer.match(/"end_line"\s*:\s*(\d+)/);
      if (st._editPath && slM && elM && !st._editFetching) {
        st._editFetching = true;
        st._editStartLine = parseInt(slM[1]);
        st._editEndLine = parseInt(elM[1]);
        const ctxN = parseInt(localStorage.getItem('context_lines')) || 2;
        const fetchStart = Math.max(1, st._editStartLine - ctxN);
        const fetchEnd = st._editEndLine + ctxN;
        fetch('/api/file-lines', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({path: st._editPath, start: fetchStart, end: fetchEnd})
        }).then(r => r.json()).then(data => {
          if (data.ok) {
            st._editOldLines = data.lines;
            st._editFetchStart = data.start;
            st._editTotal = data.total;
            st._editCtxN = ctxN;
            st._editParsed = true;
            st._dirty = true;
            requestAnimationFrame(() => this._renderStreamingEdit(st, contentEl));
          }
        }).catch(() => {});
      }
    }

    const markers = ['"new_text":"', '"new_text": "', '"content":"', '"content": "'];
    if (st._contentStart == null) {
      for (const marker of markers) {
        const pos = st.buffer.indexOf(marker);
        if (pos !== -1) { st._contentStart = pos + marker.length; break; }
      }
    }

    if (st._editParsed && st._editOldLines && st._contentStart != null) {
      const raw = st.buffer.slice(st._contentStart);
      const newText = raw.replace(/\\n/g, '\n').replace(/\\t/g, '\t')
                         .replace(/\\"/g, '"').replace(/\\"$/,'').replace(/"$/,'');
      const newLines = newText.split('\n');
      const ctxN = st._editCtxN || 2;
      const sl = st._editStartLine;
      const el = st._editEndLine;
      const oldAll = st._editOldLines;
      const fetchStart = st._editFetchStart;
      const total = st._editTotal;

      let html = '';
      const preCtxEnd = Math.min(ctxN, sl - fetchStart);
      const hiddenBefore = fetchStart - 1;
      if (hiddenBefore > 0) html += '<div class="diff-hidden">··· ' + hiddenBefore + ' lines hidden ···</div>';
      for (let i = 0; i < preCtxEnd; i++) {
        const ln = fetchStart + i;
        html += '<div class="diff-line context"><span class="diff-marker"> </span><span class="read-lineno">' + ln + '</span>' + esc(oldAll[i] || '') + '</div>';
      }
      for (let i = preCtxEnd; i < preCtxEnd + (el - sl + 1) && i < oldAll.length; i++) {
        const ln = fetchStart + i;
        html += '<div class="diff-line removed"><span class="diff-marker">-</span><span class="read-lineno">' + ln + '</span>' + esc(oldAll[i] || '') + '</div>';
      }
      for (let j = 0; j < newLines.length; j++) {
        html += '<div class="diff-line added"><span class="diff-marker">+</span><span class="read-lineno">+</span>' + esc(newLines[j]) + '</div>';
      }
      const postCtxStart = preCtxEnd + (el - sl + 1);
      for (let i = postCtxStart; i < oldAll.length; i++) {
        const ln = fetchStart + i;
        html += '<div class="diff-line context"><span class="diff-marker"> </span><span class="read-lineno">' + ln + '</span>' + esc(oldAll[i] || '') + '</div>';
      }
      const hiddenAfter = total - (fetchStart + oldAll.length - 1);
      if (hiddenAfter > 0) html += '<div class="diff-hidden">··· ' + hiddenAfter + ' lines hidden ···</div>';

      contentEl.innerHTML = html;
      contentEl.className = contentEl.className.replace('streaming-edit', 'streaming-edit diff-view');
    } else if (st._contentStart != null) {
      contentEl.textContent = st.buffer.slice(st._contentStart);
    }
  }

  _extractThinkContent(st) {
    if (st._contentStart != null) {
      return st.buffer.slice(st._contentStart);
    }
    const markers = ['"thought":"', '"thought": "', '"content":"', '"content": "'];
    for (const marker of markers) {
      const pos = st.buffer.indexOf(marker);
      if (pos !== -1) {
        st._contentStart = pos + marker.length;
        return st.buffer.slice(st._contentStart);
      }
    }
    return st.buffer;
  }

  _renderToolStreamEnd(evt) {
    const idx = evt.index || 0;
    const st = this._streamingTools && this._streamingTools[idx];
    if (!st) return sleep(0);

    const isThink = st.name === 'think';
    const isEdit = st.name === 'edit_file' || st.name === 'write_file' || st.name === 'edit';

    const statusEl = st.el.querySelector('[data-tc=status]');
    if (isThink) {
      if (statusEl) statusEl.remove();
      st.el.classList.remove('expanded');
      const descEl = st.el.querySelector('.tool-desc');
      if (descEl) descEl.textContent = 'Thought';
      this.lastToolEl = null;
    } else {
      if (statusEl) {
        statusEl.className = 'tool-status running';
        statusEl.innerHTML = '<div class="spinner spinner-sm"></div>';
      }
      const descEl = st.el.querySelector('.tool-desc');
      if (descEl && isEdit) descEl.textContent = 'Applying edit...';
      this.lastToolEl = st.el;
    }

    delete this._streamingTools[idx];
    return sleep(0);
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

  _renderFileSummary(evt) {
    const files = evt.files || [];
    if (!files.length) return sleep(0);

    for (const f of files) {
      const key = f.path || f.name;
      if (this._taskFiles[key]) {
        this._taskFiles[key].added = f.added || 0;
        this._taskFiles[key].removed = f.removed || 0;
      } else {
        this._taskFiles[key] = {
          name: f.name, path: f.path || f.name,
          type: f.type || 'edit',
          added: f.added || 0, removed: f.removed || 0
        };
      }
    }

    this._updateTaskFileBar();

    const count = files.length;
    let filesHtml = files.map(f => {
      const tag = f.type === 'new' ? '<span class="file-tag-new">new</span>' : '';
      let stat = '';
      if (f.added || f.removed) {
        const parts = [];
        if (f.added) parts.push('<span class="added-count">+' + f.added + '</span>');
        if (f.removed) parts.push('<span class="removed-count">-' + f.removed + '</span>');
        stat = '<span class="file-stat">' + parts.join(' ') + '</span>';
      }
      return '<div class="file-summary-item">' + renderFileIcon(f.name) + ' ' + esc(f.name) + ' ' + tag + ' ' + stat + '</div>';
    }).join('');
    this._appendAnimated('div', 'file-summary',
      '<div class="file-summary-header" onclick="this.parentElement.classList.toggle(\'expanded\')">'
      + '<i class="bx bx-chevron-right file-summary-chevron"></i>'
      + '<span>' + count + ' file' + (count > 1 ? 's' : '') + ' modified</span>'
      + '</div>'
      + '<div class="file-summary-list">' + filesHtml + '</div>');
    if (typeof window._adaptLogoBrightness === 'function') {
      setTimeout(window._adaptLogoBrightness, 50);
    }
    this._modifiedFiles = [];
    return sleep(200);
  }

  async _renderComplete(evt) {
    await sleep(300);
    this._modifiedFiles = [];
    this.clearAllTrackers();
    const reason = evt.reason || 'done';
    this._lastCompleteReason = reason;

    if (this._llmRequestEl) {
      const spinner = this._llmRequestEl.querySelector('.model-spinner');
      if (spinner) {
        if (reason === 'cancelled' || reason === 'error') {
          spinner.outerHTML = '<i class="bx bx-x-circle" style="color:var(--red);font-size:14px;"></i>';
        } else {
          spinner.style.display = 'none';
        }
      }
    }

    let elapsed = evt.elapsed_s || 0;
    if (!elapsed && this._taskStartTime) {
      elapsed = Math.round((Date.now() - this._taskStartTime) / 1000);
    }
    this._taskStartTime = null;
    const m = Math.floor(elapsed / 60);
    const s = elapsed % 60;

    let icon, label, cls;
    if (reason === 'cancelled') {
      icon = '<i class="bx bx-x-circle" style="font-size:14px;"></i>';
      label = 'Task cancelled by user';
      cls = 'task-complete task-cancelled';
    } else if (reason === 'error') {
      icon = '<i class="bx bx-x-circle" style="font-size:14px;"></i>';
      label = 'Task failed, please try again';
      cls = 'task-complete task-failed';
    } else if (reason === 'round_limit') {
      icon = '<i class="bx bx-error-circle" style="font-size:14px;"></i>';
      const rnd = evt.round || '?';
      const lim = evt.turn_limit || '?';
      label = `Round limit reached (${rnd}/${lim})`;
      cls = 'task-complete task-limit';
    } else {
      icon = CHECK_SVG;
      label = 'Task completed';
      cls = 'task-complete';
    }

    if (elapsed > 0) {
      const timeLabel = m > 0 ? `${m}m ${s}s` : `${s}s`;
      this.renderCenterNotice('<i class="bx bx-time-five" style="font-size:13px;vertical-align:middle;"></i> ' + timeLabel);
    }
    this._appendAnimated('div', cls, icon + ' ' + label);

    this._taskActive = false;
    if (reason !== 'error') {
      this._updateTaskFileBar(true);
    }
  }

  /* ── Persistent File Bar ── */

  _updateTaskFileBar(showActions = false) {
    const files = Object.values(this._taskFiles);
    if (!files.length) {
      this._removeTaskFileBar();
      return;
    }

    if (!this._taskFileBarEl) {
      this._taskFileBarEl = document.createElement('div');
      this._taskFileBarEl.className = 'task-file-bar';
      const inputArea = this.chatArea.closest('.chat-container')
        ? this.chatArea.closest('.chat-container').querySelector('.input-area')
        : document.querySelector('.input-area');
      if (inputArea) {
        inputArea.parentElement.insertBefore(this._taskFileBarEl, inputArea);
      } else {
        this.chatArea.parentElement.appendChild(this._taskFileBarEl);
      }
    }

    const count = files.length;
    const filesHtml = files.map(f => {
      const tag = f.type === 'new' ? '<span class="file-tag-new">new</span>' : '';
      const parts = [];
      if (f.added) parts.push('<span class="added-count">+' + f.added + '</span>');
      if (f.removed) parts.push('<span class="removed-count">-' + f.removed + '</span>');
      const stat = parts.length ? '<span class="file-stat">' + parts.join(' ') + '</span>' : '';
      const fileActions = showActions
        ? '<span class="file-item-actions">'
          + '<button class="file-item-btn reject" title="Reject" data-path="' + esc(f.path) + '" onclick="event.stopPropagation();window._revertFile(this)"><i class="bx bx-x"></i></button>'
          + '<button class="file-item-btn accept" title="Accept" data-path="' + esc(f.path) + '" onclick="event.stopPropagation();window._acceptFile(this)"><i class="bx bx-check"></i></button>'
          + '</span>'
        : '';
      return '<div class="file-summary-item" data-path="' + esc(f.path) + '">' + renderFileIcon(f.name) + ' ' + esc(f.name) + ' ' + tag + ' ' + stat + fileActions + '</div>';
    }).join('');

    const actionsHtml = showActions
      ? '<div class="task-file-actions">'
        + '<button class="task-file-btn task-file-revert" data-action="revert">Revert all</button>'
        + '<button class="task-file-btn task-file-save" data-action="save">Accept all</button>'
        + '</div>'
      : '';

    let totalAdded = 0, totalRemoved = 0;
    files.forEach(f => { totalAdded += f.added || 0; totalRemoved += f.removed || 0; });
    let totalStat = '';
    if (totalAdded || totalRemoved) {
      const tp = [];
      if (totalAdded) tp.push('<span class="added-count">+' + totalAdded + '</span>');
      if (totalRemoved) tp.push('<span class="removed-count">-' + totalRemoved + '</span>');
      totalStat = '<span class="file-stat" style="margin-left:6px;">' + tp.join(' ') + '</span>';
    }

    this._taskFileBarEl.innerHTML =
      '<div class="file-summary-header">'
      + '<i class="bx bx-chevron-right file-summary-chevron"></i>'
      + '<span>' + count + ' File' + (count > 1 ? 's' : '') + '</span>'
      + totalStat
      + actionsHtml
      + '</div>'
      + '<div class="file-summary-list">' + filesHtml + '</div>';

    if (typeof window._adaptLogoBrightness === 'function') {
      setTimeout(window._adaptLogoBrightness, 50);
    }

    const header = this._taskFileBarEl.querySelector('.file-summary-header');
    header.addEventListener('click', (e) => {
      if (e.target.closest('.task-file-btn')) return;
      this._taskFileBarEl.classList.toggle('expanded');
    });

    if (showActions) {
      this._taskFileBarEl.classList.add('expanded');
      const revertBtn = this._taskFileBarEl.querySelector('[data-action=revert]');
      const saveBtn = this._taskFileBarEl.querySelector('[data-action=save]');
      const actionsDiv = this._taskFileBarEl.querySelector('.task-file-actions');
      if (revertBtn) {
        revertBtn.addEventListener('click', async (e) => {
          e.stopPropagation();
          revertBtn.disabled = true;
          if (saveBtn) saveBtn.disabled = true;
          this._taskFileBarEl.classList.add('expanded');
          const rejectBtns = [...this._taskFileBarEl.querySelectorAll('.file-item-btn.reject')];
          for (const b of rejectBtns) {
            if (!b.closest('.file-summary-item.rejected') && !b.closest('.file-summary-item.accepted')) {
              await window._revertFile(b);
            }
          }
          if (actionsDiv) {
            actionsDiv.innerHTML = '<span class="task-file-status-label" style="color:var(--red);font-size:11px;font-weight:600;">Reverted</span>';
          }
          this._taskFileBarEl.querySelectorAll('.file-item-actions').forEach(a => a.remove());
        });
      }
      if (saveBtn) {
        saveBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          saveBtn.disabled = true;
          if (revertBtn) revertBtn.disabled = true;
          this._taskFileBarEl.classList.add('expanded');
          const acceptBtns = [...this._taskFileBarEl.querySelectorAll('.file-item-btn.accept')];
          acceptBtns.forEach(b => {
            if (!b.closest('.file-summary-item.accepted') && !b.closest('.file-summary-item.rejected')) {
              window._acceptFile(b);
            }
          });
          if (actionsDiv) {
            actionsDiv.innerHTML = '<span class="task-file-status-label" style="color:var(--green);font-size:11px;font-weight:600;">Accepted</span>';
          }
          this._taskFileBarEl.querySelectorAll('.file-item-actions').forEach(a => a.remove());
        });
      }
    }
  }

  _removeTaskFileBar() {
    if (this._taskFileBarEl) {
      this._taskFileBarEl.remove();
      this._taskFileBarEl = null;
    }
  }

  /* ── LLM API Events ── */

  _renderLLMRequest(evt) {
    const provider = evt.provider || 'LLM';
    const round = evt.round || 1;
    const model = evt.model || '';
    this._currentProvider = provider;
    this._currentRound = round;
    this._pendingLLMModel = model;
    this._pendingLLMOpts = { self_operate: evt.self_operate, env: evt.env, self_name: evt.self_name };
    if (evt.self_operate) this._selfOperate = true;
    if (!this._taskStartTime) this._taskStartTime = Date.now();
    this._llmRoundStartTime = Date.now();
    this._streamingCharCount = 0;
    this._llmRequestEl = this._createModelInfoEl(provider, round, model, {
      self_operate: evt.self_operate,
      env: evt.env,
      self_name: evt.self_name,
      waiting: true,
    });
    this._llmConnected = false;
    this.chatArea.appendChild(this._llmRequestEl);
    if (typeof _adaptLogoBrightness === 'function') _adaptLogoBrightness();
    return sleep(100);
  }

  _renderLLMResponseStart(evt) {
    if (this._llmRequestEl && !this._llmConnected) {
      this._llmConnected = true;
      this._streamingInputTokens = evt.prompt_tokens || 0;
    }
    if (this._llmRequestEl) {
      const spinner = this._llmRequestEl.querySelector('.model-spinner');
      if (spinner) spinner.style.display = '';
      const latency = this._llmRequestEl.querySelector('.model-latency');
      if (latency) latency.innerHTML = '';
      this._startStreamingBannerUpdates();
    }
    return sleep(50);
  }

  _startStreamingBannerUpdates() {
    this._stopStreamingBannerUpdates();
    this._streamingBannerInterval = setInterval(() => {
      if (!this._llmRequestEl) {
        this._stopStreamingBannerUpdates();
        return;
      }
      this._updateStreamingBanner();
    }, 500);
  }

  _stopStreamingBannerUpdates() {
    if (this._streamingBannerInterval) {
      clearInterval(this._streamingBannerInterval);
      this._streamingBannerInterval = null;
    }
  }

  _updateStreamingBanner() {
    if (!this._llmRequestEl) return;
    const latencyEl = this._llmRequestEl.querySelector('.model-latency');
    if (!latencyEl) return;

    const elapsed = ((Date.now() - (this._llmRoundStartTime || Date.now())) / 1000).toFixed(1);
    const estOutputTokens = Math.round(this._streamingCharCount / 3.5);
    const inputTokens = this._streamingInputTokens || 0;

    const sep = () => { const s = document.createElement('span'); s.textContent = ' \u00b7 '; s.className = 'model-sep'; return s; };

    latencyEl.innerHTML = '';
    const isSelfOperate = this._selfOperate;

    latencyEl.appendChild(sep());

    const fmtT = (n) => n >= 1000 ? (n / 1000).toFixed(1) + 'k' : String(n);
    const tokenStr = inputTokens > 0
      ? fmtT(inputTokens) + ' + ' + fmtT(estOutputTokens) + ' tokens'
      : '~' + fmtT(estOutputTokens) + ' tokens';
    const tokenSpan = document.createElement('span');
    tokenSpan.textContent = tokenStr;
    latencyEl.appendChild(tokenSpan);

    if (!isSelfOperate) {
      const pricing = this._getModelPricing(this._currentProvider);
      if (pricing && !pricing.free_tier) {
        const estCost = (inputTokens * pricing.input_per_1m / 1e6)
          + (estOutputTokens * pricing.output_per_1m / 1e6);
        const sym = pricing.currency === 'CNY' ? '\u00a5' : (this._costCurrency || '$');
        latencyEl.appendChild(sep());
        const costSpan = document.createElement('span');
        costSpan.textContent = sym + estCost.toFixed(4);
        latencyEl.appendChild(costSpan);
      }
    }

    latencyEl.appendChild(sep());
    const timeSpan = document.createElement('span');
    timeSpan.textContent = elapsed + 's';
    latencyEl.appendChild(timeSpan);

    latencyEl.appendChild(sep());
    const mode = (typeof window !== 'undefined' && window.currentMode) || 'agent';
    const actLabel = document.createElement('span');
    actLabel.className = 'model-activity';
    actLabel.textContent = mode === 'agent' ? 'Working' : 'Responding';
    latencyEl.appendChild(actLabel);
  }

  _getModelPricing(provider) {
    if (typeof window._modelPricing === 'object' && window._modelPricing[provider]) {
      return window._modelPricing[provider];
    }
    return null;
  }

  _trackStreamingChars(charCount) {
    this._streamingCharCount = (this._streamingCharCount || 0) + charCount;
  }

  _renderLLMResponseEnd(evt) {
    this._stopStreamingBannerUpdates();
    if (this._llmRequestEl) {
      const spinner = this._llmRequestEl.querySelector('.model-spinner');
      if (spinner) {
        if (evt.error) {
          spinner.outerHTML = '<i class="bx bx-x-circle" style="color:var(--red);font-size:14px;"></i>';
        } else {
          spinner.style.display = 'none';
        }
      }

      const usage = evt.usage || {};
      const outTokens = usage.completion_tokens || 0;
      const ctxTokens = usage.prompt_tokens || 0;
      const totalTokens = usage.total_tokens || (ctxTokens + outTokens);

      const roundData = {
        round: evt.round,
        provider: evt.provider || '',
        model: evt.model || '',
        output_tokens: outTokens,
        context_tokens: ctxTokens,
        total_tokens: totalTokens,
        latency_s: evt.latency_s || 0,
        cost: usage.cost || 0,
        timestamp: Date.now(),
        usage_raw: usage,
      };
      this._roundHistory.push(roundData);
      if (this._roundHistory.length > this._maxRoundHistory) {
        this._roundHistory.shift();
      }

      const ridx = this._roundHistory.length - 1;
      const isSelfOperate = this._selfOperate;
      const elapsed = evt.latency_s || ((Date.now() - (this._llmRoundStartTime || Date.now())) / 1000).toFixed(1);
      const latLabel = elapsed ? elapsed + 's' : '';

      const fmtTokens = (n) => n >= 1000 ? (n / 1000).toFixed(1) + 'k' : String(n);
      const tokenLabel = ctxTokens > 0
        ? fmtTokens(ctxTokens) + ' + ' + fmtTokens(outTokens) + ' tokens'
        : fmtTokens(outTokens) + ' tokens';
      const costLabel = isSelfOperate ? ''
        : (usage.cost != null ? (this._costCurrency || '$') + usage.cost.toFixed(4) : '$0.00');
      let ctxLabel = '';
      if (!isSelfOperate && ctxTokens > 0) {
        const ctxStr = ctxTokens >= 1000 ? (ctxTokens / 1000).toFixed(1) + 'k' : String(ctxTokens);
        if (this._maxContextTokens && this._maxContextTokens > 0) {
          const pct = ((ctxTokens / this._maxContextTokens) * 100).toFixed(1);
          ctxLabel = ctxStr + '(' + pct + '%) ctx';
        } else {
          ctxLabel = ctxStr + ' ctx';
        }
      }

      const latency = this._llmRequestEl.querySelector('.model-latency');
      if (latency) {
        latency.innerHTML = '';
        const makeLink = (text, idx) => {
          const a = document.createElement('span');
          a.textContent = text;
          a.className = 'debug-link';
          a.dataset.roundIdx = idx;
          a.addEventListener('click', () => this._showRoundDetail(idx));
          return a;
        };
        const sep = () => { const s = document.createElement('span'); s.textContent = ' \u00b7 '; s.className = 'model-sep'; return s; };
        latency.appendChild(sep());
        latency.appendChild(makeLink(tokenLabel, ridx));
        if (costLabel) { latency.appendChild(sep()); latency.appendChild(document.createTextNode(costLabel)); }
        if (latLabel) { latency.appendChild(sep()); latency.appendChild(document.createTextNode(latLabel)); }
        if (ctxLabel) { latency.appendChild(sep()); latency.appendChild(makeLink(ctxLabel, ridx)); }
      }

      this._lastLLMResponseEnd = evt;
      this._llmRequestEl = null;
    }
    return sleep(100);
  }

  _renderModelDecisionStart(evt) {
    const div = document.createElement('div');
    div.className = 'model-info model-decision';
    div.innerHTML =
      '<i class="bx bx-bot model-info-icon" style="color:var(--accent);font-size:16px;"></i>'
      + '<span class="model-name" style="color:var(--text-2);">Choosing the model provider</span>'
      + '<div class="spinner spinner-sm model-spinner"></div>';
    this._modelDecisionEl = div;
    this.chatArea.appendChild(div);
    this._scrollEnd();
    return sleep(100);
  }

  _renderModelDecisionEnd(evt) {
    if (this._modelDecisionEl) {
      const chosen = evt.chosen;
      if (chosen) {
        const resolveNameFn = typeof resolveDisplayName === 'function' ? resolveDisplayName : null;
        const names = typeof MODEL_DISPLAY_NAMES !== 'undefined' ? MODEL_DISPLAY_NAMES : {};
        const displayName = resolveNameFn ? resolveNameFn(chosen) : (names[chosen] || chosen);
        this._modelDecisionEl.querySelector('.model-name').textContent = displayName;
        const spinner = this._modelDecisionEl.querySelector('.model-spinner');
        if (spinner) spinner.style.display = 'none';
        if (this._onAutoModelChosen) this._onAutoModelChosen(chosen);
      } else {
        this._modelDecisionEl.querySelector('.model-name').textContent = 'No model available';
        this._modelDecisionEl.querySelector('.model-name').style.color = 'var(--red)';
        const spinner = this._modelDecisionEl.querySelector('.model-spinner');
        if (spinner) spinner.style.display = 'none';
      }
      this._modelDecisionEl = null;
    }
    return sleep(100);
  }

  _renderModelDecisionProposed(evt) {
    if (!this._modelDecisionEl) {
      this._renderModelDecisionStart({text: 'Choosing the model provider'});
    }
    if (this._modelDecisionEl) {
      const proposed = evt.proposed;
      const resolveNameFn = typeof resolveDisplayName === 'function' ? resolveDisplayName : null;
      const names = typeof MODEL_DISPLAY_NAMES !== 'undefined' ? MODEL_DISPLAY_NAMES : {};
      const displayName = resolveNameFn ? resolveNameFn(proposed) : (names[proposed] || proposed);
      const nameEl = this._modelDecisionEl.querySelector('.model-name');
      nameEl.textContent = `Choosing the model provider (${displayName})`;
    }
    return sleep(100);
  }

  _renderModelConfirmed(evt) {
    if (this._modelDecisionEl) {
      const provider = evt.provider;
      const el = this._createModelInfoEl(provider);
      this._modelDecisionEl.replaceWith(el);
      this._modelDecisionEl = null;
    }
    if (this._onAutoModelChosen) this._onAutoModelChosen(evt.provider);
    return sleep(100);
  }

  onAutoModelChosen(cb) { this._onAutoModelChosen = cb; }

  setMaxRoundHistory(n) {
    this._maxRoundHistory = n;
    while (this._roundHistory.length > n) this._roundHistory.shift();
  }

  _showRoundDetail(idx) {
    const data = this._roundHistory[idx];
    if (!data) return;
    let overlay = document.getElementById('round-detail-overlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'round-detail-overlay';
      overlay.className = 'round-detail-overlay';
      overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.classList.remove('open'); });
      document.body.appendChild(overlay);
    }
    const u = data.usage_raw || {};
    overlay.innerHTML = `<div class="round-detail-card">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <strong style="font-size:14px;">Round ${data.round} Detail</strong>
        <span style="cursor:pointer;font-size:18px;color:var(--text-3);" onclick="this.closest('.round-detail-overlay').classList.remove('open')">&times;</span>
      </div>
      <table class="round-detail-table">
        <tr><td>Provider</td><td>${esc(data.provider)}</td></tr>
        <tr><td>Model</td><td>${esc(data.model)}</td></tr>
        <tr><td>Input Tokens</td><td class="token-link" data-type="input" data-round="${data.round}">${data.context_tokens.toLocaleString()}</td></tr>
        <tr><td>Output Tokens</td><td class="token-link" data-type="output" data-round="${data.round}">${data.output_tokens.toLocaleString()}</td></tr>
        <tr><td>Total Tokens</td><td class="token-link" data-type="context" data-round="${data.round}">${data.total_tokens.toLocaleString()}</td></tr>
        <tr><td>Latency</td><td>${data.latency_s}s</td></tr>
        ${this._selfOperate ? '' : `<tr><td>Cost</td><td>${(this._costCurrency || '$') + data.cost.toFixed(6)}</td></tr>`}
        <tr><td>Time</td><td>${new Date(data.timestamp).toLocaleTimeString()}</td></tr>
        ${u.prompt_tokens_details ? `<tr><td>Prompt Details</td><td><pre style="margin:0;font-size:11px;">${esc(JSON.stringify(u.prompt_tokens_details, null, 2))}</pre></td></tr>` : ''}
        ${u.completion_tokens_details ? `<tr><td>Completion Details</td><td><pre style="margin:0;font-size:11px;">${esc(JSON.stringify(u.completion_tokens_details, null, 2))}</pre></td></tr>` : ''}
      </table>
      <div style="margin-top:12px;font-size:11px;color:var(--text-3);">
        History: ${this._roundHistory.length} / ${this._maxRoundHistory} rounds retained
      </div>
    </div>`;
    overlay.querySelectorAll('.token-link').forEach(td => {
      td.addEventListener('click', () => {
        const type = td.dataset.type;
        const round = td.dataset.round;
        const sid = this.activeSessionId;
        if (sid && type && round != null) {
          window.open(`/session/${sid}/${type}/${round}`, '_blank');
        }
      });
    });
    overlay.classList.add('open');
  }

  setCostCurrency(symbol) {
    this._costCurrency = symbol;
  }

  _createModelInfoEl(provider, round, model, opts) {
    opts = opts || {};
    const resolveNameFn = typeof resolveDisplayName === 'function' ? resolveDisplayName : null;
    const resolveLogoFn = typeof resolveModelLogo === 'function' ? resolveModelLogo : null;
    const logos = typeof MODEL_LOGOS !== 'undefined' ? MODEL_LOGOS : {};
    const names = typeof MODEL_DISPLAY_NAMES !== 'undefined' ? MODEL_DISPLAY_NAMES : {};
    const envLogos = typeof ENV_LOGOS !== 'undefined' ? ENV_LOGOS : {};

    let name, logo;
    if (opts.self_operate && opts.env) {
      const envParts = (opts.env || '').split('/');
      const envKey = envParts[envParts.length - 1] || '';
      const envLabel = envKey.charAt(0).toUpperCase() + envKey.slice(1);
      name = opts.self_name ? envLabel + ' (' + opts.self_name + ')' : envLabel;
      logo = envLogos[envKey.toLowerCase()] || envLogos[opts.env] || '';
    } else {
      name = resolveNameFn ? resolveNameFn(provider, model) : (names[provider] || provider);
      logo = resolveLogoFn ? resolveLogoFn(provider) : (logos[provider] || '');
    }

    const div = document.createElement('div');
    div.className = 'model-info';
    let html = '';
    if (logo) {
      html += '<img src="' + logo + '" alt="' + esc(name) + '" class="logo-adaptive" crossorigin="anonymous" onerror="this.style.display=\'none\'">';
    } else {
      html += '<i class="bx bx-bot model-info-icon"></i>';
    }
    html += '<span class="model-name">' + esc(name) + '</span>';
    html += '<span class="model-latency">';
    if (opts.waiting) {
      html += '<span class="model-sep"> \u00b7 </span>';
      html += '<span class="model-waiting">Connecting</span>';
    }
    html += '</span>';
    html += '<div class="spinner spinner-sm model-spinner"></div>';
    div.innerHTML = html;
    return div;
  }

  renderCenterNotice(html) {
    return this._appendAnimated('div', 'center-notice', '<div class="center-notice-inner">' + html + '</div>');
  }

  _renderNotice(evt) {
    const text = evt.text || evt.message || '';
    if (!text) return;
    const levelIcons = { info: 'bx-info-circle', success: 'bx-check-circle', warning: 'bx-error' };
    const levelColors = { info: 'var(--accent)', success: 'var(--status-ok)', warning: 'var(--orange)' };
    const level = evt.level || '';
    const icon = evt.icon ? '<i class="bx ' + evt.icon + '"></i> '
      : (levelIcons[level] ? '<i class="bx ' + levelIcons[level] + '" style="color:' + levelColors[level] + '"></i> ' : '');
    const html = icon + esc(text);

    if (evt.replace && evt.id) {
      const existing = this.chatArea.querySelector('[data-notice-id="' + evt.id + '"]');
      if (existing) {
        existing.querySelector('.center-notice-inner').innerHTML = html;
        return sleep(100);
      }
    }

    const el = this.renderCenterNotice(html);
    if (evt.id && el) el.setAttribute('data-notice-id', evt.id);
    return sleep(200);
  }

  _renderDebugNotice(evt) {
    if (!this._debugMode) return;
    const el = document.createElement('div');
    el.className = 'debug-block';
    el.style.display = 'block';
    el.innerHTML = `<div class="debug-block-inner"><div class="debug-block-header"><span class="debug-type" style="color:var(--orange);">NUDGE</span><span class="debug-sep">\u00b7</span><span>${esc(evt.text || '')}</span></div></div>`;
    this.chatArea.appendChild(el);
    this._scrollEnd();
    return sleep(100);
  }

  _renderAskUser(evt) {
    const el = this._appendAnimated('div', 'ask-user-block',
      '<div class="ask-user-icon"><i class="bx bx-question-mark"></i></div>'
      + '<div class="ask-user-text">' + md(evt.question || 'Agent is asking for your input') + '</div>');
    return sleep(300);
  }

  /* ── Tool Call Block ── */

  _naturalToolDesc(name, desc, cmd, file) {
    if (name === 'read' || name === 'read_file') {
      const fname = file || cmd || desc || '';
      const short = fname.split('/').pop() || 'file';
      const cleanDesc = desc ? desc.replace(/^Read\s+/i, '') : '';
      const displayLabel = cleanDesc || short;
      return { label: 'Read ' + displayLabel, icon: fileExtIcon(fname), expandable: true, isRead: true, fname: fname, readLabel: displayLabel };
    }
    if (name === 'write_file' || name === 'edit_file' || name === 'edit') {
      const fname = file || cmd || '';
      const cleanPath = fname.replace(/^(write|edit)\s+/, '');
      const short = cleanPath.split('/').pop() || desc || 'file';
      const isNew = name === 'write_file';
      return { label: 'Edited ' + short, icon: fileExtIcon(cleanPath), expandable: true, isEdit: true, isNew, fname: cleanPath };
    }
    if (name === 'search') {
      const raw = desc || cmd || '';
      const cleaned = raw.replace(/^Search(?:ed)?\s+(?:for\s+)?/i, '');
      const label = 'Searched ' + (cleaned || raw);
      const short = label.length > 50 ? label.slice(0, 47) + '...' : label;
      return { label: short, icon: 'bx-search', expandable: true };
    }
    if (name === 'exec') {
      const cmdText = cmd || desc || '';
      const short = desc || (cmdText.length > 50 ? cmdText.slice(0, 47) + '...' : cmdText);
      return { label: short, icon: 'bx-terminal', expandable: true };
    }
    if (name === 'todo') {
      return { label: 'Updated tasks', icon: 'bx-list-check', expandable: false };
    }
    if (name === 'ask_user') {
      return { label: 'Asked user', icon: 'bx-help-circle', expandable: true };
    }
    if (name === 'think') {
      return { label: 'Thought', icon: 'bx-brain', expandable: true, isThink: true };
    }
    return { label: (desc || name), icon: 'bx-code', expandable: true };
  }

  _makeToolCall(name, desc, cmd, file) {
    const info = this._naturalToolDesc(name, desc, cmd, file);
    let headerContent;

    if (info.isEdit) {
      const short = (info.fname || '').split('/').pop() || info.fname;
      const newTag = info.isNew ? '<span class="tool-file-tag">new</span>' : '';
      const iconHtml = info.icon && info.icon.startsWith('_devicon_:')
        ? '<img src="' + info.icon.slice(10) + '" style="width:13px;height:13px;" alt="">'
        : '<i class="bx ' + (info.icon || 'bx-code-alt') + '" style="font-size:13px"></i>';
      headerContent =
        '<div class="tool-call-chevron"><i class="bx bx-chevron-right"></i></div>'
        + '<div class="tool-icon edit">' + iconHtml + '</div>'
        + '<span class="tool-desc">Edited <span class="tool-file-link" data-op="edit">' + escWbr(short) + '</span></span>'
        + newTag
        + '<span class="diff-stats" data-tc="diffstats"></span>'
        + '<div class="tool-status running" data-tc="status"><div class="spinner spinner-sm"></div></div>';
    } else if (info.isRead) {
      const readIconHtml = info.icon && info.icon.startsWith('_devicon_:')
        ? '<img src="' + info.icon.slice(10) + '" class="tool-natural-icon" style="width:14px;height:14px;" alt="">'
        : '<i class="bx ' + (info.icon || 'bx-file') + ' tool-natural-icon"></i>';
      headerContent =
        '<div class="tool-call-chevron"><i class="bx bx-chevron-right"></i></div>'
        + readIconHtml
        + '<span class="tool-desc">Read <span class="tool-file-link" data-op="read">' + escWbr(info.readLabel || '') + '</span></span>'
        + '<span class="diff-stats" data-tc="diffstats"></span>'
        + '<div class="tool-status running" data-tc="status"><div class="spinner spinner-sm"></div></div>';
    } else if (info.isThink) {
      headerContent =
        '<div class="tool-call-chevron"><i class="bx bx-chevron-right"></i></div>'
        + '<i class="bx bx-brain tool-natural-icon"></i>'
        + '<span class="tool-desc">Thinking...</span>'
        + '<div class="tool-status running" data-tc="status"><div class="spinner spinner-sm"></div></div>';
    } else {
      const otherIconHtml = info.icon && info.icon.startsWith('_devicon_:')
        ? '<img src="' + info.icon.slice(10) + '" class="tool-natural-icon" style="width:14px;height:14px;" alt="">'
        : '<i class="bx ' + (info.icon || 'bx-code-alt') + ' tool-natural-icon"></i>';
      headerContent =
        '<div class="tool-call-chevron"><i class="bx bx-chevron-right"></i></div>'
        + otherIconHtml
        + '<span class="tool-desc">' + escWbr(info.label) + '</span>'
        + (info.detail ? '<span class="tool-detail">' + esc(info.detail) + '</span>' : '')
        + '<div class="tool-status running" data-tc="status"><div class="spinner spinner-sm"></div></div>';
    }

    const bodyContent = (info.isEdit || info.isRead)
      ? '<div class="tool-terminal" data-tc="output" style="background:transparent;max-height:400px"></div>'
      : '<div class="tool-terminal" data-tc="output"></div>';

    const expandable = info.isEdit || info.isRead || info.expandable;
    const el = this._appendAnimated('div', 'tool-call' + (expandable ? '' : ' no-expand'),
      '<div class="tool-call-header" onclick="' + (expandable ? "this.parentElement.classList.toggle('expanded')" : '') + '">'
      + headerContent + '</div>'
      + '<div class="tool-call-body">' + bodyContent + '</div>');

    if (info.isEdit) {
      el.dataset.toolType = info.isNew ? 'write' : 'edit';
    } else if (name === 'search') {
      el.dataset.toolType = 'search';
    } else if (name === 'read') {
      el.dataset.toolType = 'read';
    }
    return el;
  }

  _finishToolCall(el, ok, output, evt) {
    evt = evt || {};
    const toolName = el.dataset.toolName;
    if (toolName === 'think') {
      const s = el.querySelector('[data-tc=status]');
      if (s) s.remove();
      el.classList.remove('expanded');
      const descEl = el.querySelector('.tool-desc');
      if (descEl) descEl.textContent = 'Thought';
      const out = el.querySelector('[data-tc=output]');
      if (out && output) {
        out.style.whiteSpace = 'pre-wrap';
        out.style.background = 'transparent';
        out.textContent = output;
      }
      return;
    }
    const s = el.querySelector('[data-tc=status]');
    if (s) {
      s.className = 'tool-status ' + (ok ? 'success' : 'error');
      s.innerHTML = ok ? CHECK_SVG : FAIL_SVG;
    }
    if (output) {
      const out = el.querySelector('[data-tc=output]');
      if (out) {
        const toolType = el.dataset.toolType;
        if (toolType === 'edit') {
          if (output === '(no change)') {
            const stats = el.querySelector('[data-tc=diffstats]');
            if (stats) stats.innerHTML = '<span style="color:var(--text-3);font-style:italic;">(The assistant made no edit)</span>';
          } else {
          const diff = renderDiffOutput(output, true);
          const stats = el.querySelector('[data-tc=diffstats]');
          if (stats) {
            let parts = [];
            if (diff.addCount) parts.push('<span class="added-count">+' + diff.addCount + '</span>');
            if (diff.removeCount) parts.push('<span class="removed-count">-' + diff.removeCount + '</span>');
            stats.innerHTML = parts.join(' ');
          }
          out.innerHTML = '<div class="diff-view">' + diff.html + '</div>';
          }
        } else if (toolType === 'write') {
          const hasDiffMarkers = /^[+-]/.test(output) || /^@@hide /.test(output);
          if (hasDiffMarkers) {
            const diff = renderDiffOutput(output, true);
            const stats = el.querySelector('[data-tc=diffstats]');
            if (stats) {
              let parts = [];
              if (diff.addCount) parts.push('<span class="added-count">+' + diff.addCount + '</span>');
              if (diff.removeCount) parts.push('<span class="removed-count">-' + diff.removeCount + '</span>');
              stats.innerHTML = parts.join(' ');
            }
            out.innerHTML = '<div class="diff-view">' + diff.html + '</div>';
            el.dataset.toolType = 'edit';
          } else {
            const lines = output.split('\n');
            const bytesMatch = (output || '').match(/Written (\d+) bytes/);
            const contentMatch = (output || '').match(/Written \d+ bytes to [^\n]+\n([\s\S]*)/);
            const stats = el.querySelector('[data-tc=diffstats]');
            if (contentMatch && contentMatch[1].trim()) {
              const content = contentMatch[1];
              const contentLines = content.split('\n');
              if (stats) stats.innerHTML = '<span class="added-count">+' + contentLines.length + '</span>';
              let diffHtml = contentLines.map(l => '<div class="diff-line added">' + esc(l) + '</div>').join('');
              out.innerHTML = '<div class="diff-view">' + diffHtml + '</div>';
              el.classList.add('expanded');
            } else if (bytesMatch) {
              if (stats) stats.innerHTML = '<span class="added-count">+' + bytesMatch[1] + ' bytes</span>';
              out.innerHTML = '<div class="tool-write-result">' + esc(output) + '</div>';
            } else {
              out.textContent = output;
            }
          }
        } else if (toolType === 'read') {
          const displaySrc = evt._read_display || null;
          const stats = el.querySelector('[data-tc=diffstats]');
          if (displaySrc) {
            const rendered = _renderReadDisplay(displaySrc);
            if (stats) stats.innerHTML = '<span style="color:var(--text-3);font-size:11px;">' + rendered.readCount + ' lines read</span>';
            out.innerHTML = '<div class="diff-view">' + rendered.html + '</div>';
          } else {
            const readLines = output.split('\n');
            const lineCount = readLines.length;
            if (stats) stats.innerHTML = '<span style="color:var(--text-3);font-size:11px;">' + lineCount + ' lines</span>';
            let readHtml = '';
            const lineNumMatch = readLines[0] && readLines[0].match(/^\s*(\d+)\|/);
            if (lineNumMatch) {
              readHtml = readLines.map(l => {
                const m = l.match(/^(\s*\d+)\|(.*)/);
                if (m) return '<div class="diff-line read-line"><span class="read-lineno">' + m[1] + '</span>' + esc(m[2]) + '</div>';
                return '<div class="diff-line read-line">' + esc(l) + '</div>';
              }).join('');
            } else {
              readHtml = readLines.map(l => '<div class="diff-line read-line">' + esc(l) + '</div>').join('');
            }
            out.innerHTML = '<div class="diff-view">' + readHtml + '</div>';
          }
        } else if (toolType === 'search' && output) {
          out.innerHTML = _renderSearchOutput(output);
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

  clearAllTrackers() {
    this.execTrackers = {};
    this.callTrackers = {};
    if (this.execListEl) this.execListEl.innerHTML = '';
    if (this.callListEl) this.callListEl.innerHTML = '';
    if (this.execPanel) this.execPanel.style.display = 'none';
    if (this.callPanel) this.callPanel.style.display = 'none';
  }

  resetSessionState() {
    this.clearAllTrackers();
    this._taskFiles = {};
    this._taskActive = false;
    this._removeTaskFileBar();
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
