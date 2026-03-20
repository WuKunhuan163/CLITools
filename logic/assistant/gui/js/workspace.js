/* ── Workspace Management ── */
let currentWorkspace = localStorage.getItem('workspace_path') || '';

function setWorkspace(path) {
  currentWorkspace = (path || '').trim();
  if (currentWorkspace) {
    localStorage.setItem('workspace_path', currentWorkspace);
  } else {
    localStorage.removeItem('workspace_path');
  }
  _updateWorkspaceIndicator();
}

async function browseWorkspaceDir() {
  try {
    const r = await fetch('/api/workspace/browse', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({dir: currentWorkspace || ''})
    });
    const d = await r.json();
    if (d.ok && d.path) { setWorkspace(d.path); return; }
    if (d.error === 'Cancelled') return;
  } catch (e) { /* fallback below */ }
  const p = prompt('Workspace directory (empty to reset):', currentWorkspace);
  if (p !== null) setWorkspace(p);
}

function _updateWorkspaceIndicator(overridePath) {
  const wsPath = overridePath || currentWorkspace;
  if (overridePath && !currentWorkspace) {
    currentWorkspace = overridePath;
  }

  const titleIndicator = document.getElementById('workspace-indicator');
  if (titleIndicator) {
    const sid = activeSessionId ? activeSessionId.substring(0, 8) : '';
    if (wsPath || sid) {
      const parts = [];
      if (sid) parts.push('session: ' + sid);
      if (wsPath) parts.push('workspace: ' + wsPath);
      titleIndicator.textContent = parts.join(', ');
      titleIndicator.title = (activeSessionId || '') + (wsPath ? '\n' + wsPath : '');
      titleIndicator.style.display = '';
    } else {
      titleIndicator.style.display = 'none';
      titleIndicator.textContent = '';
    }
  }

  let badge = document.getElementById('workspace-badge');
  if (wsPath) {
    if (!badge) {
      badge = document.createElement('div');
      badge.id = 'workspace-badge';
      badge.style.cssText = 'font-size:10px;color:var(--text-3);padding:2px 12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:pointer;';
      badge.title = 'Click to change workspace';
      badge.onclick = () => browseWorkspaceDir();
      const footer = document.getElementById('sidebar-footer');
      if (footer) footer.parentElement.insertBefore(badge, footer);
    }
    const short = wsPath.length > 30 ? '...' + wsPath.slice(-27) : wsPath;
    badge.innerHTML = '<i class="bx bx-folder" style="font-size:11px;vertical-align:-1px;"></i> ' + short;
  } else if (badge) {
    badge.remove();
  }
}
