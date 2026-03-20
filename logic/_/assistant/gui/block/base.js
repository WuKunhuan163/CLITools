/**
 * Base block utilities shared across all block renderers.
 *
 * Provides:
 *   - BlockBase namespace with helper functions
 *   - Content rendering (file content with line numbers, diff rendering)
 *   - Shared block infrastructure
 */

window.BlockBase = (function() {

  /**
   * Render file content with optional line numbers.
   * Used by read_file results and edit_file content display.
   *
   * @param {string} content - Raw file content.
   * @param {Object} [opts] - Options.
   * @param {number} [opts.startLine=1] - Starting line number.
   * @param {string} [opts.lang] - Language hint for styling.
   * @param {number[]} [opts.highlightLines] - Lines to highlight.
   * @returns {string} HTML string.
   */
  function renderFileContent(content, opts = {}) {
    const startLine = opts.startLine || 1;
    const highlightSet = new Set(opts.highlightLines || []);
    const lines = content.split('\n');

    if (lines.length > 0 && lines[lines.length - 1] === '') lines.pop();
    const gutterWidth = String(startLine + lines.length - 1).length;

    return '<div class="block-file-content">' + lines.map((line, i) => {
      const lineNum = startLine + i;
      const hl = highlightSet.has(lineNum) ? ' hl' : '';
      const gutter = String(lineNum).padStart(gutterWidth, ' ');
      return `<div class="block-line${hl}"><span class="block-gutter">${gutter}</span><span class="block-code">${_esc(line) || ' '}</span></div>`;
    }).join('') + '</div>';
  }

  /**
   * Render a block header bar (like Cursor's file header).
   *
   * @param {Object} opts - Header options.
   * @param {string} opts.icon - Boxicons class or '_devicon_:url'.
   * @param {string} opts.title - Header text.
   * @param {string} [opts.badge] - Badge text (e.g. "+4").
   * @param {string} [opts.badgeClass] - CSS class for badge.
   * @param {boolean} [opts.expandable=true] - Whether clicking toggles expand.
   * @returns {string} HTML string.
   */
  function renderBlockHeader(opts) {
    let iconHtml;
    if (opts.icon && opts.icon.startsWith('_devicon_:')) {
      iconHtml = `<img src="${opts.icon.slice(10)}" class="block-header-icon" alt="">`;
    } else if (opts.icon) {
      iconHtml = `<i class="bx ${opts.icon} block-header-icon"></i>`;
    } else {
      iconHtml = '';
    }

    const badge = opts.badge ? `<span class="block-header-badge ${opts.badgeClass || ''}">${_esc(opts.badge)}</span>` : '';
    const title = `<span class="block-header-title">${_esc(opts.title)}</span>`;

    return `<div class="block-header">${iconHtml}${title}${badge}</div>`;
  }

  function _esc(s) {
    const d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
  }

  return { renderFileContent, renderBlockHeader };
})();
