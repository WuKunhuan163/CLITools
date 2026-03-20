function formatDebugUsage(evt) {
  const parts = [];
  const usage = evt.usage || {};
  const pt = usage.prompt_tokens || 0;
  const ct = usage.completion_tokens || 0;
  const total = pt + ct;
  if (total > 0) parts.push(`${total} tokens`);
  if (usage.cost != null) {
    parts.push(`$${usage.cost.toFixed(4)}`);
  } else if (total > 0) {
    parts.push('$0.00');
  }
  if (evt.latency_s) parts.push(`${evt.latency_s}s`);
  return parts.length ? parts.join(' · ') : '';
}

const DEBUG_EVENT_TYPES = new Set([
  'llm_request', 'llm_response_start', 'llm_response_end',
  'tool', 'tool_result', 'text', 'user', 'complete',
  'thinking', 'experience', 'ask_user', 'notice', 'file_summary',
  'tool_stream_start', 'tool_stream_delta', 'tool_stream_end'
]);

function createDebugBlock(evt) {
  if (!DEBUG_EVENT_TYPES.has(evt.type)) return null;
  const div = document.createElement('div');
  div.className = 'debug-block';
  const typeName = evt.type || 'unknown';
  const usageLine = formatDebugUsage(evt);
  const usageHtml = usageLine
    ? `<span class="debug-usage">${esc(usageLine)}</span><span class="debug-sep">·</span>`
    : '';
  const preview = JSON.stringify(evt).slice(0, 80);
  const fullJson = JSON.stringify(evt, null, 2);
  div.innerHTML = `
    <div class="debug-block-inner">
      <div class="debug-block-header" onclick="this.parentElement.parentElement.classList.toggle('expanded')">
        <i class="bx bx-clipboard debug-copy" title="Copy JSON" onclick="event.stopPropagation();var t=this.closest('.debug-block').querySelector('.debug-block-body').textContent;navigator.clipboard.writeText(t);this.className='bx bx-check debug-copy';setTimeout(()=>this.className='bx bx-clipboard debug-copy',1200)"></i>
        ${usageHtml}
        <span class="debug-type">${typeName}</span>
        <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(preview)}</span>
        <span class="debug-chevron"><i class="bx bx-chevron-right"></i></span>
      </div>
      <div class="debug-block-body">${esc(fullJson)}</div>
    </div>`;
  return div;
}
