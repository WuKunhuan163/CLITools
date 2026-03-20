function buildPillSelect(container, options, currentValue, onChange, opts = {}) {
  let searchable = opts.searchable !== false && options.length > 5;
  function render(filter) {
    const current = options.find(o => o.value === currentValue) || options[0];
    let iconHtml;
    if (current.logo) iconHtml = `<img src="${current.logo}" alt="">`;
    else if (current.icon) iconHtml = `<i class="bx ${current.icon}"></i>`;
    else iconHtml = '';

    const filtered = filter
      ? options.filter(o => o.label.toLowerCase().includes(filter.toLowerCase()))
      : options;

    const itemsHtml = filtered.map(o => {
      let oIcon;
      if (o.logo) oIcon = `<img src="${o.logo}" alt="">`;
      else if (o.icon) oIcon = `<i class="bx ${o.icon}"></i>`;
      else oIcon = '';
      return `<div class="pill-option${o.value === currentValue ? ' active' : ''}" data-value="${esc(o.value)}">${oIcon} ${esc(o.label)}</div>`;
    }).join('');

    const searchHtml = searchable
      ? `<div class="pill-menu-search"><input type="text" placeholder="Search..." value="${esc(filter || '')}"></div>`
      : '';

    container.innerHTML = `<button class="pill-btn">${iconHtml} ${esc(current.label)}<i class="bx bx-chevron-down pill-chevron"></i></button>`
      + `<div class="pill-menu"><div class="pill-menu-items">${itemsHtml}</div>${searchHtml}</div>`;

    const btn = container.querySelector('.pill-btn');
    const menu = container.querySelector('.pill-menu');
    btn.onclick = (e) => { e.stopPropagation(); menu.classList.toggle('open'); const si = menu.querySelector('.pill-menu-search input'); if (si) setTimeout(() => si.focus(), 50); };
    container.querySelectorAll('.pill-option').forEach(opt => {
      opt.onclick = (e) => {
        e.stopPropagation();
        currentValue = opt.dataset.value;
        menu.classList.remove('open');
        onChange(currentValue);
        render();
      };
    });
    const searchInput = menu.querySelector('.pill-menu-search input');
    if (searchInput) {
      searchInput.onclick = (e) => e.stopPropagation();
      searchInput.oninput = (e) => {
        const wasOpen = menu.classList.contains('open');
        render(e.target.value);
        if (wasOpen) container.querySelector('.pill-menu').classList.add('open');
        const ni = container.querySelector('.pill-menu-search input');
        if (ni) { ni.focus(); ni.selectionStart = ni.selectionEnd = ni.value.length; }
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
