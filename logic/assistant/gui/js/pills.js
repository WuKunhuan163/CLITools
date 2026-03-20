function buildPillSelect(container, options, currentValue, onChange, opts = {}) {
  let searchable = opts.searchable !== false && options.length > 5;

  function _buildItemsHtml(filter) {
    const filtered = filter
      ? options.filter(o => o.label.toLowerCase().includes(filter.toLowerCase()))
      : options;
    const brightness = typeof MODEL_BRIGHTNESS !== 'undefined' ? MODEL_BRIGHTNESS : {};
    return filtered.map(o => {
      let oIcon;
      if (o.logo) {
        const lb = brightness[o.value];
        const lbAttr = lb !== undefined ? ` data-logo-brightness="${lb}"` : '';
        oIcon = `<img src="${o.logo}" alt="" class="logo-adaptive" crossorigin="anonymous"${lbAttr}>`;
      }
      else if (o.icon) oIcon = `<i class="bx ${o.icon}"></i>`;
      else oIcon = '';
      return `<div class="pill-option${o.value === currentValue ? ' active' : ''}" data-value="${esc(o.value)}">${oIcon} ${esc(o.label)}</div>`;
    }).join('');
  }

  function _bindOptionClicks() {
    container.querySelectorAll('.pill-option').forEach(opt => {
      opt.onclick = (e) => {
        e.stopPropagation();
        currentValue = opt.dataset.value;
        container.querySelector('.pill-menu').classList.remove('open');
        onChange(currentValue);
        render();
      };
    });
  }

  function _updateItems(filter) {
    const itemsEl = container.querySelector('.pill-menu-items');
    if (!itemsEl) return;
    itemsEl.innerHTML = _buildItemsHtml(filter);
    _bindOptionClicks();
    if (typeof _adaptLogoBrightness === 'function') setTimeout(_adaptLogoBrightness, 30);
  }

  function render(filter) {
    const current = options.find(o => o.value === currentValue) || options[0];
    let iconHtml;
    if (current.logo) {
      const brightness = typeof MODEL_BRIGHTNESS !== 'undefined' ? MODEL_BRIGHTNESS : {};
      const lb = brightness[currentValue];
      const lbAttr = lb !== undefined ? ` data-logo-brightness="${lb}"` : '';
      iconHtml = `<img src="${current.logo}" alt="" class="logo-adaptive" crossorigin="anonymous"${lbAttr}>`;
    }
    else if (current.icon) iconHtml = `<i class="bx ${current.icon}"></i>`;
    else iconHtml = '';

    const searchHtml = searchable
      ? `<div class="pill-menu-search"><input type="text" placeholder="Search..." value="${esc(filter || '')}"></div>`
      : '';

    container.innerHTML = `<button class="pill-btn">${iconHtml} ${esc(current.label)}<i class="bx bx-chevron-down pill-chevron"></i></button>`
      + `<div class="pill-menu"><div class="pill-menu-items">${_buildItemsHtml(filter)}</div>${searchHtml}</div>`;

    const btn = container.querySelector('.pill-btn');
    const menu = container.querySelector('.pill-menu');
    btn.onclick = (e) => { e.stopPropagation(); menu.classList.toggle('open'); const si = menu.querySelector('.pill-menu-search input'); if (si) setTimeout(() => si.focus(), 50); };
    _bindOptionClicks();
    if (typeof _adaptLogoBrightness === 'function') setTimeout(_adaptLogoBrightness, 30);
    const searchInput = menu.querySelector('.pill-menu-search input');
    if (searchInput) {
      searchInput.onclick = (e) => e.stopPropagation();
      searchInput.oninput = (e) => {
        _updateItems(e.target.value);
      };
    }
  }
  render();
  document.addEventListener('click', () => {
    const m = container.querySelector('.pill-menu');
    if (m) m.classList.remove('open');
  });
  return { setValue(v) { currentValue = v; render(); }, setOptions(newOpts) { options = newOpts; searchable = opts.searchable !== false && options.length > 5; render(); } };
}

function setMode(mode) {
  selectedMode = mode;
  const welcome = $('welcome');
  if (welcome) {
    const icon = welcome.querySelector('.welcome-icon');
    if (icon) {
      icon.className = 'bx ' + (MODE_ICONS[mode] || 'bx-bot') + ' welcome-icon';
    }
  }
}

function setModel(model) {
  selectedModel = model;
  localStorage.setItem('preferred_model', model);
  fetch('/api/model/switch', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({model}),
  }).catch(err => console.warn('Model switch failed:', err));
}
function setTurnLimit(val) {
  selectedTurnLimit = parseInt(val, 10) || 0;
  fetch(`/api/session/${activeSessionId}/turn-limit`, {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({turn_limit: selectedTurnLimit})
  }).catch(() => {});
}
