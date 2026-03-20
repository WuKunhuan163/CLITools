/* ── Sidebar Toggle ── */
function toggleSidebar() {
  const sb = document.getElementById('sidebar');
  const toggleBtn = document.getElementById('sidebar-toggle');
  const icon = toggleBtn.querySelector('i');
  sb.classList.toggle('collapsed');
  toggleBtn.classList.toggle('collapsed');
  if (sb.classList.contains('collapsed')) {
    icon.className = 'bx bx-chevron-right';
  } else {
    icon.className = 'bx bx-chevron-left';
  }
}

/* ── Diff Hunk Actions ── */
window._diffHunkAction = async function(btn, action) {
  const hunk = btn.closest('.diff-hunk');
  if (!hunk || hunk.classList.contains('decided')) return;

  const toolCall = hunk.closest('.tool-call');
  if (!toolCall || toolCall.classList.contains('decided')) return;

  const sid = toolCall.dataset.sid;
  const fname = toolCall.dataset.toolCmd || '';
  const cleanPath = fname.replace(/^(write|edit)\s+/, '');

  if (action === 'accept') {
    hunk.classList.add('accepted', 'decided');
    hunk.querySelectorAll('.diff-hunk-actions').forEach(a => a.remove());

    const allToolCalls = [...document.querySelectorAll('.tool-call[data-tool-type="edit"]')];
    const fileTCs = allToolCalls.filter(tc => {
      const cmd = (tc.dataset.toolCmd || '').replace(/^(write|edit)\s+/, '');
      return cmd === cleanPath;
    });
    const myIdx = fileTCs.indexOf(toolCall);
    for (let i = 0; i <= myIdx; i++) {
      const tc = fileTCs[i];
      if (tc.classList.contains('reverted') || tc.classList.contains('decided')) continue;
      tc.classList.add('decided');
      tc.querySelectorAll('.diff-hunk:not(.rejected)').forEach(h => {
        h.classList.add('accepted', 'decided');
        h.querySelectorAll('.diff-hunk-actions').forEach(a => a.remove());
      });
    }
  } else if (action === 'reject') {
    const allToolCalls = [...document.querySelectorAll('.tool-call[data-tool-type="edit"]')];
    const fileTCs = allToolCalls.filter(tc => {
      const cmd = (tc.dataset.toolCmd || '').replace(/^(write|edit)\s+/, '');
      return cmd === cleanPath;
    });
    const myIdx = fileTCs.indexOf(toolCall);

    for (let i = fileTCs.length - 1; i >= myIdx; i--) {
      const tc = fileTCs[i];
      if (tc.classList.contains('decided') || tc.classList.contains('reverted')) continue;
      const cmd = (tc.dataset.toolCmd || '').replace(/^(write|edit)\s+/, '');
      const hunks = [...tc.querySelectorAll('.diff-hunk:not(.rejected)')].reverse();
      for (const h of hunks) {
        const removed = h.dataset.removed || '';
        const added = h.dataset.added || '';
        try {
          const res = await fetch('/api/revert-hunk', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sid, path: cmd, old_text: added, new_text: removed }),
          });
          const data = await res.json();
          if (data.ok) {
            h.classList.add('rejected', 'decided');
            h.querySelectorAll('.diff-line.added, .diff-line.removed').forEach(line => {
              line.classList.remove('added', 'removed');
              line.classList.add('read-line');
            });
            h.querySelectorAll('.diff-hunk-actions').forEach(a => a.remove());
          }
        } catch (e) { console.warn('Revert error:', e); }
      }
      const remaining = tc.querySelectorAll('.diff-hunk:not(.rejected)');
      if (!remaining.length) {
        const statusEl = tc.querySelector('[data-tc=status]');
        if (statusEl) {
          statusEl.className = 'tool-status error';
          statusEl.innerHTML = '<i class="bx bx-x" style="font-size:16px;"></i>';
        }
        const stats = tc.querySelector('[data-tc=diffstats]');
        if (stats) stats.innerHTML = '<span style="color:var(--text-3);font-style:italic">' + _('reverted') + '</span>';
        tc.classList.add('reverted', 'decided');
      }
    }
  }
};

window._acceptFile = function(btn) {
  const item = btn.closest('.file-summary-item');
  if (!item || item.classList.contains('accepted') || item.classList.contains('rejected')) return;
  item.classList.add('accepted');
  const actions = item.querySelector('.file-item-actions');
  if (actions && !actions.querySelector('.file-result-icon')) {
    actions.insertAdjacentHTML('beforeend', '<i class="bx bx-check file-result-icon accept-icon"></i>');
  }

  const filePath = item.dataset.path;
  if (filePath) {
    const allToolCalls = [...document.querySelectorAll('.tool-call[data-tool-type="edit"]')];
    for (const tc of allToolCalls) {
      const cmd = (tc.dataset.toolCmd || '').replace(/^(write|edit)\s+/, '');
      if (cmd !== filePath) continue;
      if (tc.classList.contains('reverted') || tc.classList.contains('decided')) continue;
      tc.classList.add('decided');
      tc.querySelectorAll('.diff-hunk:not(.rejected)').forEach(h => h.classList.add('accepted'));
      tc.querySelectorAll('.diff-hunk-actions').forEach(a => a.remove());
    }
  }
};

window._scheduleFileRemoval = function(item) {
  setTimeout(() => {
    item.classList.add('removing');
    setTimeout(() => {
      const path = item.dataset.path || '';
      item.remove();
      if (path && typeof engine !== 'undefined') {
        delete engine._taskFiles[path];
      }
      window._checkFileBarEmpty();
    }, 300);
  }, 2000);
};

window._checkFileBarEmpty = function() {
  if (typeof engine === 'undefined' || !engine._taskFileBarEl) return;
  const remaining = engine._taskFileBarEl.querySelectorAll('.file-summary-item:not(.removing)');
  if (!remaining.length) {
    engine._taskFileBarEl.classList.add('removing');
    setTimeout(() => engine._removeTaskFileBar(), 300);
  } else {
    const count = remaining.length;
    const header = engine._taskFileBarEl.querySelector('.file-summary-header span');
    if (header) header.textContent = count + ' File' + (count > 1 ? 's' : '');
  }
};

window._revertFile = async function(btn) {
  const filePath = btn.dataset.path;
  if (!filePath) return;
  const item = btn.closest('.file-summary-item');

  const allToolCalls = [...document.querySelectorAll('.tool-call[data-tool-type="edit"]')];
  const fileTCs = allToolCalls.filter(tc => {
    const cmd = (tc.dataset.toolCmd || '').replace(/^(write|edit)\s+/, '');
    return cmd === filePath;
  });

  let reverted = 0, failed = 0;
  const reverseFileTCs = [...fileTCs].reverse();
  for (const tc of reverseFileTCs) {
    if (tc.classList.contains('decided') || tc.classList.contains('reverted')) continue;
    const cmd = (tc.dataset.toolCmd || '').replace(/^(write|edit)\s+/, '');
    const hunks = [...tc.querySelectorAll('.diff-hunk:not(.rejected)')].reverse();
    for (const hunk of hunks) {
      const removed = hunk.dataset.removed || '';
      const added = hunk.dataset.added || '';
      const sid = tc.dataset.sid;
      try {
        const res = await fetch('/api/revert-hunk', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sid, path: cmd, old_text: added, new_text: removed }),
        });
        const data = await res.json();
        if (data.ok) { hunk.classList.add('rejected'); reverted++; }
        else { failed++; console.warn('Revert failed for hunk:', data.error); }
      } catch (e) { failed++; console.warn('Revert error:', e); }
    }
    if (!failed) {
      const statusEl = tc.querySelector('[data-tc=status]');
      if (statusEl) {
        statusEl.className = 'tool-status error';
        statusEl.innerHTML = '<i class="bx bx-x" style="font-size:16px;"></i>';
      }
      const stats = tc.querySelector('[data-tc=diffstats]');
      if (stats) stats.innerHTML = '<span style="color:var(--text-3);font-style:italic">' + _('reverted') + '</span>';
      tc.classList.add('reverted', 'decided');
      tc.querySelectorAll('.diff-line.added, .diff-line.removed').forEach(line => {
        line.classList.remove('added', 'removed');
        line.classList.add('read-line');
      });
      tc.querySelectorAll('.diff-hunk-actions').forEach(a => a.remove());
    }
  }
  if (item && !failed) {
    item.classList.add('rejected');
    const actions = item.querySelector('.file-item-actions');
    if (actions && !actions.querySelector('.file-result-icon')) {
      actions.insertAdjacentHTML('beforeend', '<i class="bx bx-x file-result-icon reject-icon"></i>');
    }
  }
};
