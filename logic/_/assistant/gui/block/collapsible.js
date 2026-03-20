/**
 * Collapsible content blocks with fade effect.
 *
 * Provides a system for collapsing/expanding tool output content blocks.
 * When collapsed, content is truncated to a configurable number of lines
 * with a fade-to-transparent gradient at the bottom. Clicking toggles
 * between collapsed and expanded states.
 *
 * Settings (from backend session config):
 *   block_collapsed_lines  – lines visible when collapsed (default: 6)
 *   block_expanded_lines   – lines visible when expanded (default: 16)
 */

window.Collapsible = (function() {
  let _collapsedLines = 6;
  let _expandedLines = 16;
  const LINE_HEIGHT = 18;

  function configure(opts) {
    if (opts.collapsed_lines) _collapsedLines = opts.collapsed_lines;
    if (opts.expanded_lines) _expandedLines = opts.expanded_lines;
  }

  function getCollapsedHeight() { return _collapsedLines * LINE_HEIGHT; }
  function getExpandedHeight() { return _expandedLines * LINE_HEIGHT; }

  /**
   * Wrap a content element in a collapsible container.
   *
   * @param {HTMLElement} contentEl - The content element to make collapsible.
   * @param {Object} [opts] - Options.
   * @param {boolean} [opts.startExpanded=false] - Start in expanded state.
   * @param {function} [opts.onToggle] - Callback when toggled.
   * @returns {HTMLElement} The wrapper element.
   */
  function wrap(contentEl, opts = {}) {
    const wrapper = document.createElement('div');
    wrapper.className = 'collapsible-wrap';

    const inner = document.createElement('div');
    inner.className = 'collapsible-inner';
    inner.appendChild(contentEl);

    const fade = document.createElement('div');
    fade.className = 'collapsible-fade';

    const toggle = document.createElement('div');
    toggle.className = 'collapsible-toggle';
    toggle.innerHTML = '<i class="bx bx-chevron-down"></i>';

    wrapper.appendChild(inner);
    wrapper.appendChild(fade);
    wrapper.appendChild(toggle);

    function update() {
      const contentHeight = contentEl.scrollHeight || contentEl.offsetHeight;
      const collapsedH = getCollapsedHeight();
      const expandedH = getExpandedHeight();
      const isExpanded = wrapper.classList.contains('expanded');

      if (contentHeight <= collapsedH) {
        wrapper.classList.add('no-collapse');
        inner.style.maxHeight = '';
        fade.style.display = 'none';
        toggle.style.display = 'none';
        return;
      }

      wrapper.classList.remove('no-collapse');
      toggle.style.display = '';

      if (isExpanded) {
        if (contentHeight <= expandedH) {
          inner.style.maxHeight = '';
          fade.style.display = 'none';
        } else {
          inner.style.maxHeight = expandedH + 'px';
          fade.style.display = '';
        }
        toggle.innerHTML = '<i class="bx bx-chevron-up"></i>';
      } else {
        inner.style.maxHeight = collapsedH + 'px';
        fade.style.display = '';
        toggle.innerHTML = '<i class="bx bx-chevron-down"></i>';
      }
    }

    toggle.onclick = function(e) {
      e.stopPropagation();
      wrapper.classList.toggle('expanded');
      update();
      if (opts.onToggle) opts.onToggle(wrapper.classList.contains('expanded'));
    };

    if (opts.startExpanded) wrapper.classList.add('expanded');

    requestAnimationFrame(() => update());

    wrapper._updateCollapsible = update;
    return wrapper;
  }

  /**
   * Apply collapsible behavior to an existing element by wrapping its children.
   *
   * @param {HTMLElement} el - Element whose content to make collapsible.
   * @param {Object} [opts] - Options passed to wrap().
   * @returns {HTMLElement} The collapsible wrapper, or null if el has no content.
   */
  function apply(el, opts = {}) {
    if (!el || !el.firstChild) return null;
    const content = document.createElement('div');
    while (el.firstChild) content.appendChild(el.firstChild);
    const w = wrap(content, opts);
    el.appendChild(w);
    return w;
  }

  /**
   * Refresh all collapsible wrappers (e.g. after streaming content changes).
   */
  function refreshAll() {
    document.querySelectorAll('.collapsible-wrap').forEach(w => {
      if (w._updateCollapsible) w._updateCollapsible();
    });
  }

  return { configure, wrap, apply, refreshAll, getCollapsedHeight, getExpandedHeight };
})();
