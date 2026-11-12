'use strict';

(() => {
  const { esc, validarRutChileno, bindLiveRutFeedback } = window.ClinicaValidators;
  const API = window.ClinicaAPI;

  const SERVICIOS_CATALOGO = [
    'Mantención Física',
    'Mantención Lógica',
    'Formateo / Instalación de SO',
  ];

  const ALL_STATES = [
    'Preinscrito',
    'Recibido',
    'En proceso',
    'En espera',
    'Listo para entrega',
    'En custodia',
    'Entregado conforme',
    'Devuelto sin reparación',
  ];

  const VIEW_ROLES = {
    qr: ['PUBLIC', 'RECEPCIONISTA', 'TECNICO', 'DOCENTE_PO'],
    lookup: ['PUBLIC', 'RECEPCIONISTA', 'TECNICO', 'DOCENTE_PO'],
    ticket_ok: ['PUBLIC', 'RECEPCIONISTA', 'TECNICO', 'DOCENTE_PO'],
    mesa: ['RECEPCIONISTA', 'DOCENTE_PO'],
    ingreso: ['RECEPCIONISTA', 'DOCENTE_PO'],
    taller: ['TECNICO', 'DOCENTE_PO'],
    bitacora: ['RECEPCIONISTA', 'TECNICO', 'DOCENTE_PO'],
    prueba: ['TECNICO', 'DOCENTE_PO'],
    aviso: ['RECEPCIONISTA', 'DOCENTE_PO'],
    salida: ['RECEPCIONISTA', 'DOCENTE_PO'],
    custodia: ['RECEPCIONISTA', 'DOCENTE_PO'],
    incidencias: ['RECEPCIONISTA', 'TECNICO', 'DOCENTE_PO'],
    print: ['RECEPCIONISTA', 'TECNICO', 'DOCENTE_PO'],
    admin: ['DOCENTE_PO'],
    metricas: ['DOCENTE_PO'],
    seguridad: ['DOCENTE_PO'],
  };

  const ICONS = {
    qr: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><path d="M14 14h3v3h-3zM18 18h3v3h-3zM18 14h3M14 19v2"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
    users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    clipboard: '<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>',
    wrench: '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    fileText: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/>',
    checkCircle: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
    phone: '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z"/>',
    package: '<path d="M16.5 9.4 7.5 4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
    lock: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    alert: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    printer: '<polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>',
    settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
    chart: '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
    shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    clock: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    plus: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
    refresh: '<polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>',
    x: '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
  };

  function ico(name) {
    const body = ICONS[name] || ICONS.clipboard;
    return `<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
  }

  const state = {
    auth: { authenticated: false, rol: 'PUBLIC', full_name: '', username: '', seccion: '' },
    dbOk: false,
    dbVendor: 'postgresql',
    currentView: 'qr',
    activeTicketNumber: 'PC-024',
    activeFicha: null,
    fichasList: [],
    lastCreatedTicket: null,
    lookupResult: null,
    lookupError: '',
    qrPrefill: null,
    triajeQuery: '',
    triajeData: null,
    adminPlantillas: null,
    adminNomina: null,
    metricasData: null,
    auditoriaData: null,
    surveyStars: 5,
    lastLatency: 0,
  };

  const appShellEl = document.getElementById('app-shell');
  const mainEl = document.getElementById('main-content');
  const sideNavEl = document.getElementById('side-navigation');
  const userChipEl = document.getElementById('user-session-chip');
  const pickerWrapEl = document.getElementById('ticket-picker-wrap');
  const ticketSelectEl = document.getElementById('select-active-ticket');
  const btnOpenAuth = document.getElementById('btn-open-auth');
  const btnLogout = document.getElementById('btn-logout');
  const btnScenarios = document.getElementById('btn-open-scenarios');
  const hdrDbBadgeEl = document.getElementById('hdr-db-badge');
  const toastStackEl = document.getElementById('toast-stack');
  const modalBackdropEl = document.getElementById('app-modal');
  const modalContentEl = document.getElementById('app-modal-content');

  // ---------------------------------------------------------------------------
  // UTILIDADES UI
  // ---------------------------------------------------------------------------
  function showToast(message, variant = 'info') {
    while (toastStackEl.children.length >= 1) {
      toastStackEl.firstElementChild.remove();
    }
    const item = document.createElement('div');
    item.className = `toast-item ${variant}`;
    item.textContent = message;
    item.title = 'Clic para cerrar';
    item.addEventListener('click', () => item.remove());
    toastStackEl.appendChild(item);
    setTimeout(() => item.remove(), 3500);
  }

  function updateLatency(ms) {
    state.lastLatency = Number(Math.max(0.01, ms / 1000).toFixed(2));
  }

  async function timedApi(fn) {
    const t0 = performance.now();
    try {
      return await fn();
    } finally {
      updateLatency(performance.now() - t0);
    }
  }

  function openModal(html, onBind) {
    modalContentEl.innerHTML = html;
    modalBackdropEl.classList.add('open');
    modalContentEl.querySelectorAll('[data-close-modal]').forEach(btn => {
      btn.addEventListener('click', closeModal);
    });
    if (onBind) onBind(modalContentEl);
  }

  function closeModal() {
    modalBackdropEl.classList.remove('open');
    modalContentEl.innerHTML = '';
  }

  function statusBadgeClass(st) {
    const map = {
      Preinscrito: 'badge-preinscrito',
      Recibido: 'badge-recibido',
      'En proceso': 'badge-proceso',
      'En espera': 'badge-espera',
      'Listo para entrega': 'badge-listo',
      'En custodia': 'badge-custodia',
      'Entregado conforme': 'badge-entregado',
      'Devuelto sin reparación': 'badge-devuelto',
    };
    return map[st] || 'badge-recibido';
  }

  function roleShortLabel(rol) {
    return (
      {
        PUBLIC: 'Visitante',
        RECEPCIONISTA: 'Recepción',
        TECNICO: 'Técnico',
        DOCENTE_PO: 'Docente PO',
      }[rol] || rol
    );
  }

  function initials(name) {
    return (
      String(name || 'U')
        .trim()
        .split(/\s+/)
        .slice(0, 2)
        .map(w => w.charAt(0).toUpperCase())
        .join('') || 'U'
    );
  }

  function hasRole(viewId) {
    const allowed = VIEW_ROLES[viewId] || [];
    return allowed.includes(state.auth.rol);
  }

  function getStepIndexForStatus(st) {
    return (
      {
        Preinscrito: 1,
        Recibido: 2,
        'En proceso': 3,
        'En espera': 3,
        'Listo para entrega': 5,
        'Entregado conforme': 6,
        'Devuelto sin reparación': 6,
        'En custodia': 7,
      }[st] || 1
    );
  }

  function ticketStripHtml(f) {
    if (!f) return '';
    const prop = f.propietario || {};
    const dev = f.dispositivo || {};
    const serieInfo = dev.es_clon
      ? `Clon interno <span class="mono">${esc(dev.codigo_interno_clon || 'Por asignar')}</span>`
      : `Serie <span class="mono">${esc(dev.numero_serie || 'Pendiente')}</span>`;

    const flowSteps = [
      { idx: 2, view: 'ingreso', label: 'Recepción' },
      { idx: 3, view: 'taller', label: 'Taller' },
      { idx: 4, view: 'bitacora', label: 'Bitácora' },
      { idx: 5, view: 'prueba', label: 'Control calidad' },
      { idx: 6, view: 'aviso', label: 'Aviso' },
      { idx: 7, view: 'salida', label: 'Entrega' },
      { idx: 8, view: 'custodia', label: 'Custodia' },
    ];
    const currentStepIdx = getStepIndexForStatus(f.estado);

    return `
      <div class="ticket-strip">
        <div class="ticket-strip-top">
          <div>
            <div class="ticket-id">
              <span>${esc(f.numero_ticket)}</span>
              <span class="badge-status ${statusBadgeClass(f.estado)}">${esc(f.estado)}</span>
              ${f.hallazgo_ilicito_ley_21459 ? '<span class="badge-status badge-espera">Retención Ley 21.459</span>' : ''}
              ${f.incidencia_activa && !f.hallazgo_ilicito_ley_21459 ? '<span class="badge-status badge-recibido">Incidencia abierta</span>' : ''}
            </div>
            <div class="card-subtitle">
              Titular: <strong>${esc(prop.nombre_completo || '—')}</strong> (${esc(prop.rut || '—')}) ·
              Equipo: <strong>${esc(dev.codigo_dispositivo || '—')} · ${esc(dev.marca_modelo || '—')}</strong> · ${serieInfo}
            </div>
          </div>
          <div style="text-align: right; font-size: 12px; color: var(--ink-secondary);">
            <div>Checklist: <strong>${f.checklist_total - f.checklist_pendientes}/${f.checklist_total}</strong> tareas</div>
            <div>${esc((f.servicios || []).join(' + '))}</div>
          </div>
        </div>
        <div class="ticket-progress">
          ${flowSteps
            .map((s, i) => {
              const isAct = state.currentView === s.view;
              const isDone = s.idx <= currentStepIdx && !isAct;
              const canOpen = hasRole(s.view);
              return `
                ${i > 0 ? '<span class="tp-sep">/</span>' : ''}
                <button type="button" class="tp-step ${isAct ? 'active' : ''} ${isDone ? 'done' : ''}" data-step-goto="${esc(s.view)}" ${canOpen ? '' : 'disabled'}>
                  ${esc(s.label)}
                </button>
              `;
            })
            .join('')}
        </div>
      </div>
    `;
  }

  // ---------------------------------------------------------------------------
  // CARGA DE DATOS DESDE DJANGO + POSTGRESQL
  // ---------------------------------------------------------------------------
  async function checkHealth() {
    const textEl = hdrDbBadgeEl.querySelector('.status-text');
    try {
      const h = await timedApi(() => API.get('/health/'));
      state.dbOk = h && h.status === 'ok';
      state.dbVendor = (h && h.database_vendor) || 'postgresql';
      hdrDbBadgeEl.classList.remove('err');
      hdrDbBadgeEl.classList.add('ok');
      textEl.textContent = `PostgreSQL OK (${state.dbVendor})`;
    } catch (_) {
      state.dbOk = false;
      hdrDbBadgeEl.classList.remove('ok');
      hdrDbBadgeEl.classList.add('err');
      textEl.textContent = 'Base de datos sin conexión';
    }
  }

  async function refreshSession(keepView = false) {
    try {
      const me = await timedApi(() => API.get('/auth/me/'));
      state.auth = me && me.authenticated ? me : { authenticated: false, rol: 'PUBLIC' };
    } catch (_) {
      state.auth = { authenticated: false, rol: 'PUBLIC' };
    }

    if (state.auth.authenticated) {
      await loadFichasList();
      if (!keepView) {
        if (state.auth.rol === 'RECEPCIONISTA') state.currentView = 'mesa';
        else if (state.auth.rol === 'TECNICO') state.currentView = 'taller';
        else if (state.auth.rol === 'DOCENTE_PO') state.currentView = 'metricas';
      }
      await loadActiveFicha(state.activeTicketNumber);
      await navigate(state.currentView);
      return;
    } else {
      state.fichasList = [];
      state.activeFicha = null;
      if (!keepView && !['qr', 'lookup', 'ticket_ok'].includes(state.currentView)) {
        state.currentView = 'qr';
      }
    }
    renderAll();
  }

  async function loadFichasList() {
    if (!state.auth.authenticated) return;
    try {
      const rows = await timedApi(() => API.get('/fichas/'));
      state.fichasList = Array.isArray(rows) ? rows : [];
      if (state.fichasList.length && !state.fichasList.some(f => f.numero_ticket === state.activeTicketNumber)) {
        state.activeTicketNumber = state.fichasList[0].numero_ticket;
      }
    } catch (err) {
      showToast(err.message || 'No se pudo cargar la lista de fichas.', 'danger');
    }
  }

  async function loadActiveFicha(ticketNumber) {
    if (!state.auth.authenticated || !ticketNumber) return null;
    try {
      const detail = await timedApi(() => API.get(`/fichas/${encodeURIComponent(ticketNumber)}/`));
      state.activeTicketNumber = detail.numero_ticket;
      state.activeFicha = detail;
      return detail;
    } catch (err) {
      showToast(err.message || `Error cargando ficha ${ticketNumber}`, 'danger');
      return null;
    }
  }

  // ---------------------------------------------------------------------------
  // RENDERIZADO DEL SHELL (HEADER, SIDEBAR CONTEXTUAL)
  // ---------------------------------------------------------------------------
  function renderHeaderAndBar() {
    const isAuth = Boolean(state.auth.authenticated);
    appShellEl.classList.toggle('is-public', !isAuth);

    if (isAuth) {
      userChipEl.style.display = 'inline-flex';
      userChipEl.innerHTML = `<span class="user-avatar">${esc(initials(state.auth.full_name))}</span><span>${esc(state.auth.full_name)} · ${esc(roleShortLabel(state.auth.rol))}</span>`;
      btnOpenAuth.textContent = 'Cambiar cuenta';
      btnLogout.style.display = 'inline-flex';
      pickerWrapEl.style.display = 'flex';

      ticketSelectEl.innerHTML = state.fichasList
        .map(f => {
          const sel = f.numero_ticket === state.activeTicketNumber ? 'selected' : '';
          const cod = f.dispositivo?.codigo_dispositivo || '';
          return `<option value="${esc(f.numero_ticket)}" ${sel}>${esc(f.numero_ticket)}${cod ? ` · ${esc(cod)}` : ''} (${esc(f.estado)})</option>`;
        })
        .join('');
    } else {
      userChipEl.style.display = 'none';
      btnOpenAuth.textContent = 'Iniciar sesión';
      btnLogout.style.display = 'none';
      pickerWrapEl.style.display = 'none';
    }
  }

  function renderSidebar() {
    if (!state.auth.authenticated) {
      sideNavEl.innerHTML = '';
      return;
    }

    const groups = [
      {
        title: 'Mesón y Taller',
        items: [
          { id: 'mesa', icon: 'users', label: 'Triaje por RUT' },
          { id: 'ingreso', icon: 'clipboard', label: 'Recepción e Inspección' },
          { id: 'taller', icon: 'wrench', label: 'Checklist de Taller' },
          { id: 'bitacora', icon: 'fileText', label: 'Bitácora de Ticket' },
          { id: 'prueba', icon: 'checkCircle', label: 'Control de Calidad' },
          { id: 'aviso', icon: 'phone', label: 'Aviso de Retiro' },
          { id: 'salida', icon: 'package', label: 'Entrega y Encuesta' },
          { id: 'custodia', icon: 'lock', label: 'Custodia Nocturna' },
          { id: 'incidencias', icon: 'alert', label: 'Incidencias' },
          { id: 'print', icon: 'printer', label: 'Comprobante' },
        ],
      },
      {
        title: 'Administración',
        items: [
          { id: 'metricas', icon: 'chart', label: 'Métricas y Respaldo' },
          { id: 'admin', icon: 'settings', label: 'Plantillas y Nómina' },
          { id: 'seguridad', icon: 'shield', label: 'Auditoría y Seguridad' },
        ],
      },
      {
        title: 'Portal Público',
        items: [
          { id: 'qr', icon: 'qr', label: 'Preinscripción QR' },
          { id: 'lookup', icon: 'search', label: 'Consultar Ticket' },
        ],
      },
    ];

    const visibleGroups = groups
      .map(g => ({
        ...g,
        items: g.items.filter(it => hasRole(it.id)),
      }))
      .filter(g => g.items.length > 0);

    sideNavEl.innerHTML = visibleGroups
      .map(
        g => `
          <div class="nav-group-title">${esc(g.title)}</div>
          ${g.items
            .map(it => {
              const currentAttr = state.currentView === it.id ? 'aria-current="page"' : '';
              return `
                <button type="button" class="nav-btn" data-nav="${esc(it.id)}" ${currentAttr}>
                  ${ico(it.icon)}
                  <span>${esc(it.label)}</span>
                </button>
              `;
            })
            .join('')}
        `
      )
      .join('');
  }

  async function navigate(viewId) {
    state.currentView = viewId;
    if (state.auth.authenticated) {
      if (viewId === 'mesa') {
        await fetchTriaje(state.triajeQuery);
      } else if (['ingreso', 'taller', 'bitacora', 'prueba', 'aviso', 'salida', 'custodia', 'incidencias', 'print'].includes(viewId)) {
        await loadActiveFicha(state.activeTicketNumber);
      } else if (viewId === 'admin' && state.auth.rol === 'DOCENTE_PO') {
        await fetchAdminData();
      } else if (viewId === 'metricas' && state.auth.rol === 'DOCENTE_PO') {
        await fetchMetricas();
      } else if (viewId === 'seguridad' && state.auth.rol === 'DOCENTE_PO') {
        await fetchAuditoria();
      }
    }
    renderAll();
  }

  function renderAll() {
    renderHeaderAndBar();
    renderSidebar();
    renderCurrentView();
  }

  // ---------------------------------------------------------------------------
  // MODALES: LOGIN & CASOS DE PRUEBA PARA EVALUACIÓN
  // ---------------------------------------------------------------------------
  function openAuthModal() {
    openModal(
      `
      <div class="card-header">
        <div>
          <h2 class="card-title">${ico('lock')} Iniciar sesión institucional</h2>
          <p class="card-subtitle">Acceso para personal de Mesón, Alumnos Técnicos y Docente encargado</p>
        </div>
        <button type="button" class="btn btn-ghost btn-sm" data-close-modal aria-label="Cerrar">${ico('x')}</button>
      </div>
      <form id="login-form" class="form-grid">
        <label class="form-full">Usuario o correo institucional
          <input id="login-user" type="text" required placeholder="Ej: daniel.meliman" autocomplete="username">
        </label>
        <label class="form-full">Contraseña
          <input id="login-pass" type="password" required placeholder="Ingrese contraseña" autocomplete="current-password">
        </label>
        <div id="login-error-box" class="form-full"></div>
        <div class="form-full" style="display:flex; gap:8px; flex-wrap:wrap;">
          <button type="submit" class="btn btn-primary" style="flex:1;">Ingresar al sistema</button>
          <button type="button" class="btn btn-outline" id="btn-unlock-demo">Desbloquear demo</button>
        </div>
      </form>
      <div style="border-top: 1px solid var(--border); padding-top: 12px;">
        <div style="font-size: 11px; font-weight: 600; color: var(--ink-muted); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px;">
          Cuentas de prueba habilitadas
        </div>
        <div style="display:flex; gap:8px; flex-wrap:wrap;">
          <button type="button" class="btn btn-outline btn-sm" data-fill-user="daniel.meliman" data-fill-pass="ClinicaPC!26">
            Recepción (Daniel)
          </button>
          <button type="button" class="btn btn-outline btn-sm" data-fill-user="diego.astudillo" data-fill-pass="TallerPC!26">
            Técnico (Diego)
          </button>
          <button type="button" class="btn btn-outline btn-sm" data-fill-user="pablo.pesce" data-fill-pass="DocentePO!26">
            Docente PO (Prof. Pesce)
          </button>
        </div>
      </div>
      `,
      box => {
        const userIn = box.querySelector('#login-user');
        const passIn = box.querySelector('#login-pass');
        const errBox = box.querySelector('#login-error-box');

        box.querySelectorAll('[data-fill-user]').forEach(btn => {
          btn.addEventListener('click', () => {
            userIn.value = btn.getAttribute('data-fill-user');
            passIn.value = btn.getAttribute('data-fill-pass');
            errBox.innerHTML = '';
          });
        });

        box.querySelector('#btn-unlock-demo').addEventListener('click', async () => {
          try {
            await timedApi(() => API.post('/auth/unlock-demo/', {}));
            errBox.innerHTML = '<div class="notice notice-success"><span>Cuentas demo desbloqueadas correctamente.</span></div>';
            showToast('Contadores de bloqueo reiniciados.', 'success');
          } catch (err) {
            errBox.innerHTML = `<div class="notice notice-danger"><span>${esc(err.message)}</span></div>`;
          }
        });

        box.querySelector('#login-form').addEventListener('submit', async ev => {
          ev.preventDefault();
          errBox.innerHTML = '';
          try {
            await timedApi(() =>
              API.post('/auth/login/', {
                username: userIn.value.trim(),
                password: passIn.value,
              })
            );
            closeModal();
            showToast('Sesión iniciada correctamente.', 'success');
            await refreshSession(false);
          } catch (err) {
            errBox.innerHTML = `<div class="notice notice-danger"><span>HTTP ${err.status || 401}: ${esc(err.message)}</span></div>`;
          }
        });
      }
    );
  }

  function openScenariosModal() {
    openModal(
      `
      <div class="card-header">
        <div>
          <h2 class="card-title">${ico('shield')} Escenarios de Evaluación y Control</h2>
          <p class="card-subtitle">Accesos directos para verificar criterios CA01–CA10, Leyes 21.719/21.459 y OWASP</p>
        </div>
        <button type="button" class="btn btn-ghost btn-sm" data-close-modal aria-label="Cerrar">${ico('x')}</button>
      </div>
      <div style="display:flex; flex-direction:column; gap:8px;">
        <button type="button" class="btn btn-outline" data-sc="qr_idor" style="justify-content:flex-start;">
          1. Consulta pública e intento IDOR (Ticket PC-024 + RUT distinto)
        </button>
        <button type="button" class="btn btn-outline" data-sc="pc024_ca08" style="justify-content:flex-start;">
          2. Bloqueo Quality Gate CA08 (PC-024 con checklist incompleto)
        </button>
        <button type="button" class="btn btn-outline" data-sc="pc025_clon" style="justify-content:flex-start;">
          3. Recepción equipo clon CL-01 sin N° de serie (PC-025)
        </button>
        <button type="button" class="btn btn-outline" data-sc="pc026_ley21459" style="justify-content:flex-start;">
          4. Taller PC-026: falla imprevista CA07 o retención Ley N° 21.459
        </button>
        <button type="button" class="btn btn-outline" data-sc="pc027_tercero" style="justify-content:flex-start;">
          5. Entrega a tercero autorizado con Módulo 11 (PC-027)
        </button>
        <button type="button" class="btn btn-outline" data-sc="pc028_custodia" style="justify-content:flex-start;">
          6. Custodia 18:00 hrs y retención 60 días (PC-028)
        </button>
        <button type="button" class="btn btn-danger" data-sc="test_403" style="justify-content:flex-start;">
          7. Prueba RBAC HTTP 403 en vivo (/api/v1/admin/nomina/)
        </button>
      </div>
      <div id="scenario-probe-result"></div>
      `,
      box => {
        box.querySelectorAll('[data-sc]').forEach(btn => {
          btn.addEventListener('click', async () => {
            const sc = btn.getAttribute('data-sc');
            const out = box.querySelector('#scenario-probe-result');
            if (sc === 'test_403') {
              try {
                const res = await timedApi(() => API.get('/admin/nomina/'));
                out.innerHTML = `<div class="notice notice-success"><span>HTTP 200 OK (Docente PO autorizado): ${res.total} registros en nómina.</span></div>`;
              } catch (err) {
                out.innerHTML = `<div class="notice notice-danger"><span>HTTP ${err.status} devuelto por DRF: ${esc(err.message)}</span></div>`;
                showToast(`Control RBAC respondió HTTP ${err.status}.`, 'warning');
              }
              return;
            }

            if (sc === 'qr_idor') {
              closeModal();
              await navigate('lookup');
              return;
            }

            const map = {
              pc024_ca08: { ticket: 'PC-024', view: 'prueba' },
              pc025_clon: { ticket: 'PC-025', view: 'ingreso' },
              pc026_ley21459: { ticket: 'PC-026', view: 'taller' },
              pc027_tercero: { ticket: 'PC-027', view: 'salida' },
              pc028_custodia: { ticket: 'PC-028', view: 'custodia' },
            }[sc];
            if (!state.auth.authenticated) {
              out.innerHTML = '<div class="notice notice-warning"><span>Inicia sesión primero con Recepción, Técnico o Docente PO para abrir esta ficha.</span></div>';
              return;
            }
            state.activeTicketNumber = map.ticket;
            closeModal();
            await navigate(map.view);
          });
        });
      }
    );
  }

  // ---------------------------------------------------------------------------
  // RENDERIZADO PRINCIPAL Y CONTROL DE ACCESO
  // ---------------------------------------------------------------------------
  function renderCurrentView() {
    if (!hasRole(state.currentView)) {
      renderAccessDeniedCard();
      return;
    }

    switch (state.currentView) {
      case 'qr':
        return renderQrScreen();
      case 'lookup':
        return renderLookupScreen();
      case 'ticket_ok':
        return renderTicketOkScreen();
      case 'mesa':
        return renderMesaScreen();
      case 'ingreso':
        return renderIngresoScreen();
      case 'taller':
        return renderTallerScreen();
      case 'bitacora':
        return renderBitacoraScreen();
      case 'prueba':
        return renderPruebaScreen();
      case 'aviso':
        return renderAvisoScreen();
      case 'salida':
        return renderSalidaScreen();
      case 'custodia':
        return renderCustodiaScreen();
      case 'incidencias':
        return renderIncidenciasScreen();
      case 'print':
        return renderPrintScreen();
      case 'admin':
        return renderAdminScreen();
      case 'metricas':
        return renderMetricasScreen();
      case 'seguridad':
        return renderSeguridadScreen();
      default:
        return renderQrScreen();
    }
  }

  function renderAccessDeniedCard() {
    const needed = (VIEW_ROLES[state.currentView] || []).map(roleShortLabel).join(', ');
    mainEl.innerHTML = `
      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">${ico('lock')} Acceso restringido</h2>
            <p class="card-subtitle">Esta sección requiere perfil: ${esc(needed)}.</p>
          </div>
        </div>
        <div class="notice notice-warning">
          <span>Inicia sesión con una cuenta autorizada para continuar.</span>
          <button type="button" class="btn btn-primary btn-sm" id="btn-denied-login">Iniciar sesión</button>
        </div>
      </div>
    `;
    mainEl.querySelector('#btn-denied-login').addEventListener('click', openAuthModal);
  }

  function publicPortalHeader(activeTab) {
    return `
      <div class="public-header-row">
        <div>
          <h2 class="page-title">Atención Clínica del PC</h2>
          <p class="page-desc">Servicio técnico gratuito realizado por estudiantes de Informática INACAP Sede San Pedro de la Paz.</p>
        </div>
        <div class="segmented-tabs" role="tablist">
          <button type="button" class="seg-tab ${activeTab === 'qr' ? 'active' : ''}" id="tab-pub-qr">
            ${ico('qr')} Preinscripción
          </button>
          <button type="button" class="seg-tab ${activeTab === 'lookup' ? 'active' : ''}" id="tab-pub-lookup">
            ${ico('search')} Consultar ticket
          </button>
        </div>
      </div>
    `;
  }

  function publicInfoSidebar() {
    return `
      <aside class="card">
        <div class="card-header">
          <h3 class="card-title">${ico('clock')} Información de atención</h3>
        </div>
        <div class="info-list">
          <div class="info-list-item">
            ${ico('clipboard')}
            <div>
              <strong>Recepción presencial en Mesón</strong>
              Presenta tu número de ticket generado junto al equipo y su cargador.
            </div>
          </div>
          <div class="info-list-item">
            ${ico('lock')}
            <div>
              <strong>Retiro y custodia nocturna</strong>
              Los equipos se entregan antes de las 18:00 hrs. Los no retirados quedan en custodia en Sala de Profesores (máx. 60 días).
            </div>
          </div>
          <div class="info-list-item">
            ${ico('shield')}
            <div>
              <strong>Resguardo de datos personales</strong>
              Tus datos de contacto se utilizan solo para avisos de retiro conforme a la Ley N° 21.719.
            </div>
          </div>
        </div>
      </aside>
    `;
  }

  // ---------------------------------------------------------------------------
  // VISTA 1: PREINSCRIPCIÓN PÚBLICA QR
  // ---------------------------------------------------------------------------
  function renderQrScreen() {
    const pf = state.qrPrefill || {};
    const prefillNotice = state.qrPrefill
      ? `<div class="notice notice-info"><span>Datos prellenados para <strong>${esc(pf.nombre_completo)}</strong> (<span class="mono">${esc(pf.rut)}</span>).</span><button type="button" class="btn btn-outline btn-sm" id="btn-clear-prefill">Limpiar</button></div>`
      : '';

    mainEl.innerHTML = `
      ${!state.auth.authenticated ? publicPortalHeader('qr') : ''}
      ${!state.dbOk ? '<div class="notice notice-warning"><span>La base de datos PostgreSQL no responde en este momento. Verifica el servicio local antes de registrar.</span></div>' : ''}
      ${prefillNotice}
      <div class="${!state.auth.authenticated ? 'public-grid' : ''}">
        <div class="card">
          <div class="card-header">
            <div>
              <h2 class="card-title">${ico('qr')} Preinscripción de equipo</h2>
              <p class="card-subtitle">Completa los datos del titular y la falla observada para agilizar tu ingreso en mesón.</p>
            </div>
          </div>

          <form id="qr-form" class="form-grid">
            <label>Nombre completo del titular
              <input id="qr-nombre" type="text" required value="${esc(pf.nombre_completo || '')}" placeholder="Ej: Camila Rojas Méndez">
            </label>
            <label>RUT
              <input id="qr-rut" type="text" required value="${esc(pf.rut || '')}" placeholder="12.345.678-5">
              <div class="rut-feedback" id="qr-rut-fb"></div>
            </label>
            <label>Teléfono de contacto
              <input id="qr-tel" type="text" required value="${esc(pf.telefono || '')}" placeholder="+56 9 8765 4321">
            </label>
            <label>Correo electrónico
              <input id="qr-correo" type="email" required value="${esc(pf.correo || '')}" placeholder="nombre@correo.cl">
            </label>
            <label class="form-full">Comuna y dirección
              <input id="qr-dir" type="text" required value="${esc(pf.comuna_direccion || '')}" placeholder="San Pedro de la Paz">
            </label>
            <label>Tipo de dispositivo
              <select id="qr-tipo">
                <option value="Notebook">Notebook</option>
                <option value="Desktop / Torre">Desktop / Torre</option>
                <option value="All-in-One">All-in-One</option>
                <option value="Mini PC">Mini PC</option>
              </select>
            </label>
            <label>Marca y modelo
              <input id="qr-modelo" type="text" required placeholder="Ej: Lenovo ThinkPad T14">
            </label>
            <label class="form-full">Problema o síntoma observado
              <textarea id="qr-problema" rows="2" required placeholder="Describe brevemente qué falla presenta el equipo..."></textarea>
            </label>
            <div class="form-full">
              <div style="font-size:12px; font-weight:500; margin-bottom:6px;">Servicios requeridos</div>
              <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:8px;">
                ${SERVICIOS_CATALOGO.map(
                  (srv, i) => `
                  <label class="checkbox-tile">
                    <input type="checkbox" name="qr-srv" value="${esc(srv)}" ${i === 0 ? 'checked' : ''}>
                    <span>${esc(srv)}</span>
                  </label>`
                ).join('')}
              </div>
            </div>
            <div id="qr-err-box" class="form-full"></div>
            <div class="form-full" style="display:flex; justify-content:flex-end;">
              <button type="submit" class="btn btn-primary">Generar ticket de atención</button>
            </div>
          </form>
        </div>
        ${!state.auth.authenticated ? publicInfoSidebar() : ''}
      </div>
    `;

    const tabLookup = mainEl.querySelector('#tab-pub-lookup');
    if (tabLookup) tabLookup.addEventListener('click', () => navigate('lookup'));

    bindLiveRutFeedback(mainEl.querySelector('#qr-rut'), mainEl.querySelector('#qr-rut-fb'));
    const clearBtn = mainEl.querySelector('#btn-clear-prefill');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        state.qrPrefill = null;
        renderQrScreen();
      });
    }

    mainEl.querySelector('#qr-form').addEventListener('submit', async ev => {
      ev.preventDefault();
      const errBox = mainEl.querySelector('#qr-err-box');
      errBox.innerHTML = '';
      const rutVal = mainEl.querySelector('#qr-rut').value.trim();
      if (!validarRutChileno(rutVal)) {
        errBox.innerHTML = '<div class="notice notice-danger"><span>El RUT ingresado no es válido.</span></div>';
        return;
      }
      const servicios = Array.from(mainEl.querySelectorAll('input[name="qr-srv"]:checked')).map(c => c.value);
      if (!servicios.length) {
        errBox.innerHTML = '<div class="notice notice-danger"><span>Selecciona al menos un servicio.</span></div>';
        return;
      }
      try {
        const res = await timedApi(() =>
          API.post('/public/preinscripcion/', {
            nombre_completo: mainEl.querySelector('#qr-nombre').value.trim(),
            rut: rutVal,
            telefono: mainEl.querySelector('#qr-tel').value.trim(),
            correo: mainEl.querySelector('#qr-correo').value.trim(),
            comuna_direccion: mainEl.querySelector('#qr-dir').value.trim(),
            tipo: mainEl.querySelector('#qr-tipo').value,
            marca_modelo: mainEl.querySelector('#qr-modelo').value.trim(),
            problema_declarado: mainEl.querySelector('#qr-problema').value.trim(),
            servicios,
          })
        );
        state.lastCreatedTicket = {
          ...res,
          telefono: mainEl.querySelector('#qr-tel').value.trim(),
          correo: mainEl.querySelector('#qr-correo').value.trim(),
          comuna_direccion: mainEl.querySelector('#qr-dir').value.trim(),
        };
        state.activeTicketNumber = res.numero_ticket;
        state.qrPrefill = null;
        showToast(`Ticket ${res.numero_ticket} generado.`, 'success');
        await navigate('ticket_ok');
      } catch (err) {
        errBox.innerHTML = `<div class="notice notice-danger"><span>${esc(err.message)}</span></div>`;
      }
    });
  }

  function renderLookupScreen() {
    mainEl.innerHTML = `
      ${!state.auth.authenticated ? publicPortalHeader('lookup') : ''}
      <div class="${!state.auth.authenticated ? 'public-grid' : ''}">
        <div class="card">
          <div class="card-header">
            <div>
              <h2 class="card-title">${ico('search')} Consultar estado de atención</h2>
              <p class="card-subtitle">Ingresa tu número de ticket y el RUT del titular registrado para ver el estado actual.</p>
            </div>
          </div>

          <form id="lookup-form" class="form-grid">
            <label>Número de ticket
              <input id="lk-ticket" type="text" required value="PC-024" placeholder="Ej: PC-024">
            </label>
            <label>RUT del titular
              <input id="lk-rut" type="text" required value="12.345.678-5" placeholder="12.345.678-5">
              <div class="rut-feedback" id="lk-rut-fb"></div>
            </label>
            <div class="form-full" style="display:flex; justify-content:space-between; gap:10px; flex-wrap:wrap;">
              <button type="button" class="btn btn-outline btn-sm" id="btn-test-idor-wrong">Probar consulta con RUT distinto</button>
              <button type="submit" class="btn btn-primary">Consultar ticket</button>
            </div>
          </form>

          <div id="lookup-output">
            ${state.lookupError ? `<div class="notice notice-danger"><span>${esc(state.lookupError)}</span></div>` : ''}
            ${
              state.lookupResult
                ? `
              <div class="owner-panel">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                  <span class="ticket-id">${esc(state.lookupResult.numero_ticket)}</span>
                  <span class="badge-status ${statusBadgeClass(state.lookupResult.estado)}">${esc(state.lookupResult.estado)}</span>
                </div>
                <div><strong>Titular:</strong> ${esc(state.lookupResult.titular)} (<span class="mono">${esc(state.lookupResult.rut)}</span>)</div>
                <div><strong>Equipo:</strong> ${esc(state.lookupResult.dispositivo)}</div>
                <div><strong>Problema:</strong> ${esc(state.lookupResult.problema_declarado)}</div>
                <div><strong>Servicios:</strong> ${esc((state.lookupResult.servicios || []).join(', '))}</div>
                ${
                  state.lookupResult.ubicacion_custodia
                    ? `<div class="notice notice-warning"><span>Equipo en custodia: ${esc(state.lookupResult.ubicacion_custodia)}</span></div>`
                    : ''
                }
              </div>`
                : ''
            }
          </div>
        </div>
        ${!state.auth.authenticated ? publicInfoSidebar() : ''}
      </div>
    `;

    const tabQr = mainEl.querySelector('#tab-pub-qr');
    if (tabQr) tabQr.addEventListener('click', () => navigate('qr'));

    bindLiveRutFeedback(mainEl.querySelector('#lk-rut'), mainEl.querySelector('#lk-rut-fb'));

    const runLookup = async (ticket, rut) => {
      state.lookupError = '';
      state.lookupResult = null;
      try {
        state.lookupResult = await timedApi(() =>
          API.get(`/public/ticket/${encodeURIComponent(ticket)}/?rut=${encodeURIComponent(rut)}`)
        );
        renderLookupScreen();
      } catch (err) {
        state.lookupError = err.message || `Error HTTP ${err.status}`;
        renderLookupScreen();
      }
    };

    mainEl.querySelector('#lookup-form').addEventListener('submit', async ev => {
      ev.preventDefault();
      await runLookup(
        mainEl.querySelector('#lk-ticket').value.trim(),
        mainEl.querySelector('#lk-rut').value.trim()
      );
    });
    mainEl.querySelector('#btn-test-idor-wrong').addEventListener('click', async () => {
      mainEl.querySelector('#lk-ticket').value = 'PC-024';
      mainEl.querySelector('#lk-rut').value = '15.890.123-4';
      await runLookup('PC-024', '15.890.123-4');
    });
  }

  function renderTicketOkScreen() {
    const t = state.lastCreatedTicket;
    if (!t) return renderQrScreen();

    mainEl.innerHTML = `
      ${!state.auth.authenticated ? publicPortalHeader('qr') : ''}
      <div class="card">
        <div class="qr-card">
          <span class="badge-status badge-preinscrito">${esc(t.estado || 'Preinscrito')}</span>
          <h2 style="font-family: var(--font-mono); color: var(--brand); font-size: 26px; font-weight: 700;">${esc(t.numero_ticket)}</h2>
          <svg class="qr-svg" viewBox="0 0 100 100" aria-label="Código QR Ticket">
            <rect width="100" height="100" fill="#fff"/>
            <rect x="8" y="8" width="24" height="24" fill="none" stroke="#18181B" stroke-width="4"/>
            <rect x="14" y="14" width="12" height="12" fill="#C62828"/>
            <rect x="68" y="8" width="24" height="24" fill="none" stroke="#18181B" stroke-width="4"/>
            <rect x="74" y="14" width="12" height="12" fill="#18181B"/>
            <rect x="8" y="68" width="24" height="24" fill="none" stroke="#18181B" stroke-width="4"/>
            <rect x="14" y="74" width="12" height="12" fill="#18181B"/>
            <rect x="42" y="16" width="14" height="14" fill="#18181B"/>
            <rect x="42" y="42" width="16" height="16" fill="#C62828"/>
            <rect x="68" y="44" width="20" height="12" fill="#18181B"/>
            <rect x="44" y="68" width="12" height="22" fill="#18181B"/>
            <rect x="68" y="68" width="22" height="22" fill="#18181B"/>
          </svg>
          <div style="font-size: 13px; color: var(--ink);">
            <div><strong>Titular:</strong> ${esc(t.titular)} (<span class="mono">${esc(t.rut)}</span>)</div>
            <div><strong>Equipo:</strong> ${esc(t.codigo_dispositivo)} · ${esc(t.dispositivo)}</div>
            <div><strong>Servicios:</strong> ${esc((t.servicios || []).join(' + '))}</div>
          </div>
          <p class="card-subtitle">Presenta este código en el mesón de recepción de Clínica del PC.</p>
          <div style="display:flex; gap:8px; flex-wrap:wrap; justify-content:center;">
            <button type="button" class="btn btn-outline btn-sm" id="btn-add-another-pc">${ico('plus')} Inscribir otro equipo</button>
            <button type="button" class="btn btn-primary btn-sm" id="btn-print-qr">${ico('printer')} Imprimir comprobante</button>
          </div>
          ${
            ['RECEPCIONISTA', 'DOCENTE_PO'].includes(state.auth.rol)
              ? `<button type="button" class="btn btn-success btn-sm" id="btn-go-recep">Continuar a recepción (${esc(t.numero_ticket)})</button>`
              : ''
          }
        </div>
      </div>
    `;

    const tabQr = mainEl.querySelector('#tab-pub-qr');
    if (tabQr) tabQr.addEventListener('click', () => navigate('qr'));
    const tabLookup = mainEl.querySelector('#tab-pub-lookup');
    if (tabLookup) tabLookup.addEventListener('click', () => navigate('lookup'));

    mainEl.querySelector('#btn-add-another-pc').addEventListener('click', () => {
      state.qrPrefill = {
        nombre_completo: t.titular,
        rut: t.rut,
        telefono: t.telefono || '',
        correo: t.correo || '',
        comuna_direccion: t.comuna_direccion || '',
      };
      navigate('qr');
    });
    mainEl.querySelector('#btn-print-qr').addEventListener('click', () => window.print());
    const goRecBtn = mainEl.querySelector('#btn-go-recep');
    if (goRecBtn) {
      goRecBtn.addEventListener('click', async () => {
        state.activeTicketNumber = t.numero_ticket;
        await loadFichasList();
        await navigate('ingreso');
      });
    }
  }

  // ---------------------------------------------------------------------------
  // VISTA 2: TRIAJE MULTI-PC POR RUT
  // ---------------------------------------------------------------------------
  async function fetchTriaje(query) {
    try {
      state.triajeData = await timedApi(() => API.get(`/triaje/?q=${encodeURIComponent(query || '')}`));
    } catch (err) {
      showToast(err.message, 'danger');
    }
  }

  function openNewDeviceModal(owner) {
    openModal(
      `
      <div class="card-header">
        <div>
          <h2 class="card-title">${ico('plus')} Nuevo equipo para ${esc(owner.nombre_completo)}</h2>
          <p class="card-subtitle">RUT <span class="mono">${esc(owner.rut)}</span></p>
        </div>
        <button type="button" class="btn btn-ghost btn-sm" data-close-modal aria-label="Cerrar">${ico('x')}</button>
      </div>
      <form id="new-dev-form" class="form-grid">
        <label>Tipo de equipo
          <select id="nd-tipo">
            <option value="Notebook">Notebook</option>
            <option value="Desktop / Torre">Desktop / Torre</option>
            <option value="All-in-One">All-in-One</option>
            <option value="Mini PC">Mini PC</option>
          </select>
        </label>
        <label>Marca y modelo
          <input id="nd-modelo" type="text" required placeholder="Ej: Dell Latitude 5420">
        </label>
        <label class="form-full">Problema declarado
          <textarea id="nd-prob" rows="2" required placeholder="Motivo de ingreso..."></textarea>
        </label>
        <div class="form-full">
          <div style="font-size:12px; font-weight:500; margin-bottom:6px;">Servicios solicitados</div>
          <div style="display:flex; flex-direction:column; gap:6px;">
            ${SERVICIOS_CATALOGO.map(
              (s, i) => `
              <label class="checkbox-tile">
                <input type="checkbox" name="nd-srv" value="${esc(s)}" ${i === 0 ? 'checked' : ''}>
                <span>${esc(s)}</span>
              </label>`
            ).join('')}
          </div>
        </div>
        <div class="form-full" style="display:flex; gap:8px; justify-content:flex-end;">
          <button type="button" class="btn btn-outline" data-close-modal>Cancelar</button>
          <button type="submit" class="btn btn-primary">Registrar equipo y ticket</button>
        </div>
      </form>
      `,
      box => {
        box.querySelector('#new-dev-form').addEventListener('submit', async ev => {
          ev.preventDefault();
          const srvs = Array.from(box.querySelectorAll('input[name="nd-srv"]:checked')).map(c => c.value);
          if (!srvs.length) {
            showToast('Selecciona al menos un servicio.', 'warning');
            return;
          }
          try {
            const res = await timedApi(() =>
              API.post('/public/preinscripcion/', {
                nombre_completo: owner.nombre_completo,
                rut: owner.rut,
                telefono: owner.telefono,
                correo: owner.correo,
                comuna_direccion: owner.comuna_direccion,
                tipo: box.querySelector('#nd-tipo').value,
                marca_modelo: box.querySelector('#nd-modelo').value.trim(),
                problema_declarado: box.querySelector('#nd-prob').value.trim(),
                servicios: srvs,
              })
            );
            closeModal();
            showToast(`Equipo ${res.codigo_dispositivo} y ticket ${res.numero_ticket} registrados.`, 'success');
            await loadFichasList();
            state.activeTicketNumber = res.numero_ticket;
            await navigate('ingreso');
          } catch (err) {
            showToast(err.message, 'danger');
          }
        });
      }
    );
  }

  function renderMesaScreen() {
    const td = state.triajeData || { latencia_segundos: 0, propietarios: [] };
    mainEl.innerHTML = `
      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">${ico('users')} Triaje y búsqueda por RUT</h2>
            <p class="card-subtitle">Consulta de propietarios y equipos asociados · Respuesta SQL: <span class="mono">${esc(td.latencia_segundos)} s</span></p>
          </div>
        </div>

        <form id="triaje-search-form" style="display:flex; gap:8px; flex-wrap:wrap;">
          <input id="triaje-q" type="text" value="${esc(state.triajeQuery)}" placeholder="Buscar por RUT, nombre del titular o número de ticket..." style="flex:1; min-width:240px;">
          <button type="submit" class="btn btn-primary">${ico('search')} Buscar</button>
          <button type="button" class="btn btn-outline" id="btn-triaje-all">Ver todos</button>
        </form>

        <div style="display:flex; flex-direction:column; gap:12px;">
          ${
            !td.propietarios.length
              ? '<div class="notice notice-info"><span>No se encontraron registros para el criterio ingresado.</span></div>'
              : td.propietarios
                  .map(
                    ow => `
              <div class="owner-panel">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                  <div>
                    <strong style="font-size:14px;">${esc(ow.nombre_completo)}</strong> · <span class="mono">${esc(ow.rut)}</span>
                    <div class="card-subtitle">${esc(ow.telefono)} · ${esc(ow.correo)} · ${esc(ow.comuna_direccion)}</div>
                  </div>
                  <button type="button" class="btn btn-outline btn-sm" data-add-dev="${ow.id}">${ico('plus')} Nuevo equipo</button>
                </div>
                <div class="device-grid">
                  ${ow.dispositivos
                    .map(
                      d => `
                    <div class="device-card ${d.ficha_activa && d.ficha_activa.numero_ticket === state.activeTicketNumber ? 'selected' : ''}">
                      <div>
                        <div style="display:flex; justify-content:space-between; gap:6px; align-items:center; flex-wrap:wrap;">
                          <span class="mono">${esc(d.codigo_dispositivo)}</span>
                          ${
                            d.ficha_activa
                              ? `<span class="badge-status ${statusBadgeClass(d.ficha_activa.estado)}">${esc(d.ficha_activa.numero_ticket)} · ${esc(d.ficha_activa.estado)}</span>`
                              : ''
                          }
                        </div>
                        <div style="font-weight:600; margin-top:6px;">${esc(d.marca_modelo)}</div>
                        <div class="card-subtitle">
                          ${esc(d.tipo)} · ${d.es_clon ? `Clon ${esc(d.codigo_interno_clon || 'CL-XX')}` : `Serie ${esc(d.numero_serie || 'Pendiente')}`} ·
                          ${d.historial_count} atención(es)
                        </div>
                      </div>
                      <div style="display:flex; gap:6px; flex-wrap:wrap;">
                        ${
                          d.ficha_activa
                            ? `<button type="button" class="btn btn-primary btn-sm" data-open-ticket="${esc(d.ficha_activa.numero_ticket)}">Abrir ${esc(d.ficha_activa.numero_ticket)}</button>`
                            : ''
                        }
                        <button type="button" class="btn btn-outline btn-sm" data-new-ticket-dev="${esc(d.codigo_dispositivo)}">${ico('plus')} Nueva orden</button>
                      </div>
                    </div>`
                    )
                    .join('')}
                </div>
              </div>`
                  )
                  .join('')
          }
        </div>
      </div>
    `;

    mainEl.querySelector('#triaje-search-form').addEventListener('submit', async ev => {
      ev.preventDefault();
      state.triajeQuery = mainEl.querySelector('#triaje-q').value.trim();
      await fetchTriaje(state.triajeQuery);
      renderMesaScreen();
    });
    mainEl.querySelector('#btn-triaje-all').addEventListener('click', async () => {
      state.triajeQuery = '';
      await fetchTriaje('');
      renderMesaScreen();
    });
    mainEl.querySelectorAll('[data-open-ticket]').forEach(btn => {
      btn.addEventListener('click', async () => {
        state.activeTicketNumber = btn.getAttribute('data-open-ticket');
        const f = await loadActiveFicha(state.activeTicketNumber);
        await navigate(f && f.estado === 'Preinscrito' ? 'ingreso' : 'taller');
      });
    });
    mainEl.querySelectorAll('[data-add-dev]').forEach(btn => {
      btn.addEventListener('click', () => {
        const oid = Number(btn.getAttribute('data-add-dev'));
        const ow = td.propietarios.find(o => o.id === oid);
        if (ow) openNewDeviceModal(ow);
      });
    });
    mainEl.querySelectorAll('[data-new-ticket-dev]').forEach(btn => {
      btn.addEventListener('click', () => {
        const cod = btn.getAttribute('data-new-ticket-dev');
        openModal(
          `
          <div class="card-header">
            <div>
              <h2 class="card-title">${ico('plus')} Nueva orden de servicio (${esc(cod)})</h2>
              <p class="card-subtitle">Genera una nueva ficha asociada al equipo seleccionado</p>
            </div>
            <button type="button" class="btn btn-ghost btn-sm" data-close-modal aria-label="Cerrar">${ico('x')}</button>
          </div>
          <form id="reentry-form" style="display:flex; flex-direction:column; gap:12px;">
            <label>Motivo de ingreso
              <textarea id="re-prob" rows="2" required placeholder="Describe el motivo de la nueva atención..."></textarea>
            </label>
            <div>
              <div style="font-size:12px; font-weight:500; margin-bottom:6px;">Servicios solicitados</div>
              <div style="display:flex; flex-direction:column; gap:6px;">
                ${SERVICIOS_CATALOGO.map(
                  (s, i) => `
                  <label class="checkbox-tile">
                    <input type="checkbox" name="re-srv" value="${esc(s)}" ${i === 0 ? 'checked' : ''}>
                    <span>${esc(s)}</span>
                  </label>`
                ).join('')}
              </div>
            </div>
            <div style="display:flex; gap:8px; justify-content:flex-end;">
              <button type="button" class="btn btn-outline" data-close-modal>Cancelar</button>
              <button type="submit" class="btn btn-primary">Crear ficha</button>
            </div>
          </form>
          `,
          box => {
            box.querySelector('#reentry-form').addEventListener('submit', async ev => {
              ev.preventDefault();
              const srvs = Array.from(box.querySelectorAll('input[name="re-srv"]:checked')).map(c => c.value);
              if (!srvs.length) {
                showToast('Selecciona al menos un servicio.', 'warning');
                return;
              }
              try {
                const created = await timedApi(() =>
                  API.post(`/dispositivos/${encodeURIComponent(cod)}/nueva-ficha/`, {
                    problema_declarado: box.querySelector('#re-prob').value.trim(),
                    servicios: srvs,
                  })
                );
                closeModal();
                showToast(`Ficha ${created.numero_ticket} creada.`, 'success');
                await loadFichasList();
                state.activeTicketNumber = created.numero_ticket;
                await navigate('ingreso');
              } catch (err) {
                showToast(err.message, 'danger');
              }
            });
          }
        );
      });
    });
  }

  // ---------------------------------------------------------------------------
  // VISTA 3: RECEPCIÓN FÍSICA, EQUIPO CLON Y FIRMA DE CONSENTIMIENTO
  // ---------------------------------------------------------------------------
  function renderIngresoScreen() {
    const f = state.activeFicha;
    if (!f) return;
    const dev = f.dispositivo || {};
    const prop = f.propietario || {};
    const selectedSrvs = new Set(f.servicios || []);

    mainEl.innerHTML = `
      ${ticketStripHtml(f)}
      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">${ico('clipboard')} Inspección física y consentimiento de ingreso</h2>
            <p class="card-subtitle">Verifica número de serie, estado externo, accesorios y firma digital del titular</p>
          </div>
          ${f.consentimiento_firmado ? '<span class="badge-status badge-listo">Consentimiento firmado</span>' : ''}
        </div>

        <div class="notice notice-info">
          <span><strong>Titular:</strong> ${esc(prop.nombre_completo)} · RUT <span class="mono">${esc(prop.rut)}</span> · Tel: ${esc(prop.telefono)} · ${esc(prop.comuna_direccion)}</span>
        </div>

        <form id="ingreso-form" class="form-grid">
          <label>Tipo de dispositivo
            <select id="ing-tipo">
              ${['Notebook', 'Desktop / Torre', 'All-in-One', 'Mini PC']
                .map(t => `<option value="${esc(t)}" ${dev.tipo === t ? 'selected' : ''}>${esc(t)}</option>`)
                .join('')}
            </select>
          </label>
          <label>Marca y modelo
            <input id="ing-modelo" type="text" required value="${esc(dev.marca_modelo || '')}">
          </label>
          <label>Número de serie
            <input id="ing-serie" type="text" value="${esc(dev.numero_serie || '')}" ${dev.es_clon ? 'disabled' : ''} placeholder="Ej: PF2X9A01">
          </label>
          <label class="checkbox-tile" style="align-self:end;">
            <input id="ing-clon" type="checkbox" ${dev.es_clon ? 'checked' : ''}>
            <span>Equipo armado o clon sin número de serie (<span class="mono">${esc(dev.codigo_interno_clon || 'CL-XX automático')}</span>)</span>
          </label>

          <label>Prueba de encendido inicial
            <select id="ing-prueba">
              ${['Enciende normalmente', 'Enciende pero no da video', 'No enciende', 'Ingreso con daño físico evidente']
                .map(opt => `<option value="${esc(opt)}" ${f.prueba_inicial === opt ? 'selected' : ''}>${esc(opt)}</option>`)
                .join('')}
            </select>
          </label>
          <label>Accesorios recibidos
            <input id="ing-acc" type="text" required value="${esc(f.accesorios || '')}" placeholder="Cargador, bolso, cable de poder...">
          </label>
          <label class="form-full">Daños preexistentes observados
            <textarea id="ing-danos" rows="2" required>${esc(f.danos_preexistentes || '')}</textarea>
          </label>
          <label class="form-full">Problema declarado
            <textarea id="ing-prob" rows="2" required>${esc(f.problema_declarado || '')}</textarea>
          </label>

          <div class="form-full">
            <div style="font-size:12px; font-weight:500; margin-bottom:6px;">Servicios confirmados para ejecución en taller</div>
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:8px;">
              ${SERVICIOS_CATALOGO.map(
                srv => `
                <label class="checkbox-tile">
                  <input type="checkbox" name="ing-srv" value="${esc(srv)}" ${selectedSrvs.has(srv) ? 'checked' : ''}>
                  <span>${esc(srv)}</span>
                </label>`
              ).join('')}
            </div>
          </div>

          <div class="form-full signature-box">
            <div style="font-size:12px; font-weight:600;">Firma digital de consentimiento informado (Ley N° 21.719)</div>
            ${
              f.firma_hash_sha256
                ? `<div class="notice notice-success"><span>Registro verificado: <span class="mono">${esc(f.firma_hash_sha256)}</span></span></div>`
                : ''
            }
            <canvas id="sig-canvas" class="signature-canvas" width="600" height="120"></canvas>
            <div class="signature-tools">
              <label class="checkbox-tile" style="background:transparent; border:0; padding:0;">
                <input id="ing-consent-chk" type="checkbox" ${f.consentimiento_firmado ? 'checked' : ''}>
                <span style="font-size:12px;">El titular acepta el estado físico inicial, el servicio académico gratuito y el tratamiento de sus datos (Ley N° 21.719).</span>
              </label>
              <button type="button" class="btn btn-outline btn-sm" id="btn-clear-sig">Limpiar firma</button>
            </div>
          </div>

          <div id="ing-err" class="form-full"></div>
          <div class="form-full" style="display:flex; justify-content:flex-end;">
            <button type="submit" class="btn btn-primary">Confirmar recepción</button>
          </div>
        </form>
      </div>
    `;

    const clonChk = mainEl.querySelector('#ing-clon');
    const serieIn = mainEl.querySelector('#ing-serie');
    clonChk.addEventListener('change', () => {
      serieIn.disabled = clonChk.checked;
      if (clonChk.checked) serieIn.value = '';
    });

    const canvas = mainEl.querySelector('#sig-canvas');
    const ctx = canvas.getContext('2d');
    ctx.strokeStyle = '#18181B';
    ctx.lineWidth = 2.2;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    let drawing = false;
    let strokes = [];
    let currentStroke = [];

    const getPos = e => {
      const r = canvas.getBoundingClientRect();
      return [((e.clientX - r.left) * canvas.width) / r.width, ((e.clientY - r.top) * canvas.height) / r.height];
    };
    canvas.addEventListener('pointerdown', e => {
      drawing = true;
      canvas.setPointerCapture(e.pointerId);
      const p = getPos(e);
      currentStroke = [p];
      ctx.beginPath();
      ctx.moveTo(p[0], p[1]);
    });
    canvas.addEventListener('pointermove', e => {
      if (!drawing) return;
      const p = getPos(e);
      currentStroke.push(p);
      ctx.lineTo(p[0], p[1]);
      ctx.stroke();
    });
    const endDraw = () => {
      if (drawing && currentStroke.length) strokes.push(currentStroke);
      drawing = false;
      currentStroke = [];
    };
    canvas.addEventListener('pointerup', endDraw);
    canvas.addEventListener('pointercancel', endDraw);

    mainEl.querySelector('#btn-clear-sig').addEventListener('click', () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      strokes = [];
    });

    mainEl.querySelector('#ingreso-form').addEventListener('submit', async ev => {
      ev.preventDefault();
      const errEl = mainEl.querySelector('#ing-err');
      errEl.innerHTML = '';

      const consentChk = mainEl.querySelector('#ing-consent-chk').checked;
      if (!consentChk || (!f.consentimiento_firmado && strokes.length === 0)) {
        errEl.innerHTML = '<div class="notice notice-danger"><span>Registra la firma digital en el recuadro y acepta la cláusula de consentimiento.</span></div>';
        return;
      }
      const servicios = Array.from(mainEl.querySelectorAll('input[name="ing-srv"]:checked')).map(c => c.value);
      const svgPath = strokes.length
        ? strokes.map(pts => 'M ' + pts.map(p => `${p[0].toFixed(0)} ${p[1].toFixed(0)}`).join(' L ')).join(' ')
        : 'VERIFIED_EXISTING_CONSENT';

      try {
        const updated = await timedApi(() =>
          API.post(`/fichas/${encodeURIComponent(f.numero_ticket)}/recepcion/`, {
            tipo: mainEl.querySelector('#ing-tipo').value,
            marca_modelo: mainEl.querySelector('#ing-modelo').value.trim(),
            es_clon: clonChk.checked,
            numero_serie: serieIn.value.trim(),
            prueba_inicial: mainEl.querySelector('#ing-prueba').value,
            accesorios: mainEl.querySelector('#ing-acc').value.trim(),
            danos_preexistentes: mainEl.querySelector('#ing-danos').value.trim(),
            problema_declarado: mainEl.querySelector('#ing-prob').value.trim(),
            servicios,
            firma_aceptada: true,
            firma_trazo_svg_data: svgPath,
          })
        );
        state.activeFicha = updated;
        await loadFichasList();
        showToast(`Recepción confirmada para ${updated.numero_ticket}.`, 'success');
        renderIngresoScreen();
        renderHeaderAndBar();
      } catch (err) {
        errEl.innerHTML = `<div class="notice notice-danger"><span>${esc(err.message)}</span></div>`;
      }
    });
  }

  // ---------------------------------------------------------------------------
  // VISTA 4: CHECKLIST DE TALLER MULTI-SERVICIO
  // ---------------------------------------------------------------------------
  function renderTallerScreen() {
    const f = state.activeFicha;
    if (!f) return;
    const items = f.checklist_items || [];
    const blockedLegal = Boolean(f.hallazgo_ilicito_ley_21459);

    mainEl.innerHTML = `
      ${ticketStripHtml(f)}
      ${
        state.auth.rol === 'TECNICO'
          ? `<div class="notice notice-info">
              <span>${ico('shield')} <strong>Privacidad Ley N° 21.719:</strong> Por seguridad, los datos personales completos del titular (<span class="mono">${esc(f.propietario?.rut)}</span>) permanecen visibles solo en Mesón y Dirección.</span>
            </div>`
          : ''
      }
      ${
        blockedLegal
          ? `<div class="notice notice-danger">
              <span><strong>Intervención bloqueada (Ley N° 21.459):</strong> Equipo retenido bajo cadena de custodia hasta resolución del Docente encargado.</span>
              <button type="button" class="btn btn-outline btn-sm" id="btn-go-inc">Ver detalle</button>
            </div>`
          : ''
      }

      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">${ico('wrench')} Checklist técnico de intervención (Plantilla v${f.version_plantilla_usada}.0)</h2>
            <p class="card-subtitle">Completa o justifica técnicamente cada tarea antes de enviar el equipo a control de calidad</p>
          </div>
          <div style="display:flex; gap:8px; flex-wrap:wrap;">
            <button type="button" class="btn btn-outline btn-sm" id="btn-report-ca07" ${blockedLegal ? 'disabled' : ''}>${ico('alert')} Reportar incidencia</button>
            <button type="button" class="btn btn-danger btn-sm" id="btn-report-21459" ${blockedLegal ? 'disabled' : ''}>Hallazgo ilícito (Ley 21.459)</button>
          </div>
        </div>

        <form id="checklist-form">
          <table class="checklist-table">
            <thead>
              <tr>
                <th>Servicio</th>
                <th>Tarea</th>
                <th style="width:145px;">Estado</th>
                <th>Justificación técnica (si no aplica)</th>
              </tr>
            </thead>
            <tbody>
              ${items
                .map(
                  it => `
                <tr>
                  <td><span class="badge-status badge-preinscrito">${esc(it.servicio_nombre)}</span></td>
                  <td>
                    <div>${esc(it.descripcion_tarea)}</div>
                    ${it.actualizado_por ? `<small style="color:var(--ink-muted);">Por: ${esc(it.actualizado_por)}</small>` : ''}
                  </td>
                  <td>
                    <select class="chk-state-sel" data-key="${esc(it.clave_unica)}" ${blockedLegal ? 'disabled' : ''}>
                      ${['Pendiente', 'Realizado', 'No aplica']
                        .map(s => `<option value="${s}" ${it.estado === s ? 'selected' : ''}>${s}</option>`)
                        .join('')}
                    </select>
                  </td>
                  <td>
                    <input type="text" class="chk-just-in" data-key="${esc(it.clave_unica)}" value="${esc(it.justificacion || '')}" placeholder="Motivo técnico..." ${blockedLegal ? 'disabled' : ''}>
                  </td>
                </tr>`
                )
                .join('')}
            </tbody>
          </table>

          <div id="taller-err" style="margin-top:12px;"></div>
          <div style="display:flex; justify-content:space-between; align-items:center; gap:10px; margin-top:16px; flex-wrap:wrap;">
            <button type="button" class="btn btn-outline" id="btn-mark-all-done" ${blockedLegal ? 'disabled' : ''}>Marcar todo realizado</button>
            <div style="display:flex; gap:8px;">
              <button type="submit" class="btn btn-primary" ${blockedLegal ? 'disabled' : ''}>Guardar avance</button>
              <button type="button" class="btn btn-success" id="btn-go-step6">Control de calidad</button>
            </div>
          </div>
        </form>
      </div>
    `;

    const incBtn = mainEl.querySelector('#btn-go-inc');
    if (incBtn) incBtn.addEventListener('click', () => navigate('incidencias'));
    mainEl.querySelector('#btn-go-step6').addEventListener('click', () => navigate('prueba'));

    mainEl.querySelector('#btn-mark-all-done').addEventListener('click', () => {
      mainEl.querySelectorAll('.chk-state-sel').forEach(sel => {
        sel.value = 'Realizado';
      });
    });

    mainEl.querySelector('#checklist-form').addEventListener('submit', async ev => {
      ev.preventDefault();
      const errEl = mainEl.querySelector('#taller-err');
      errEl.innerHTML = '';
      const payloadItems = Array.from(mainEl.querySelectorAll('.chk-state-sel')).map(sel => {
        const key = sel.getAttribute('data-key');
        const just = mainEl.querySelector(`.chk-just-in[data-key="${CSS.escape(key)}"]`).value.trim();
        return { clave_unica: key, estado: sel.value, justificacion: just };
      });
      try {
        const updated = await timedApi(() =>
          API.post(`/fichas/${encodeURIComponent(f.numero_ticket)}/checklist/`, { items: payloadItems })
        );
        state.activeFicha = updated;
        await loadFichasList();
        showToast('Checklist actualizado.', 'success');
        renderTallerScreen();
        renderHeaderAndBar();
      } catch (err) {
        errEl.innerHTML = `<div class="notice notice-danger"><span>${esc(err.message)}</span></div>`;
      }
    });

    mainEl.querySelector('#btn-report-ca07').addEventListener('click', () => {
      openModal(
        `
        <div class="card-header">
          <h2 class="card-title">${ico('alert')} Reportar falla imprevista</h2>
          <button type="button" class="btn btn-ghost btn-sm" data-close-modal aria-label="Cerrar">${ico('x')}</button>
        </div>
        <form id="ca07-form" style="display:flex; flex-direction:column; gap:12px;">
          <label>Descripción técnica de la anomalía detectada
            <textarea id="ca07-desc" rows="3" required placeholder="Ej: Unidad de almacenamiento con falla crítica; requiere autorización del titular."></textarea>
          </label>
          <div style="display:flex; gap:8px; justify-content:flex-end;">
            <button type="button" class="btn btn-outline" data-close-modal>Cancelar</button>
            <button type="submit" class="btn btn-warning">Poner ficha en espera</button>
          </div>
        </form>
        `,
        box => {
          box.querySelector('#ca07-form').addEventListener('submit', async ev => {
            ev.preventDefault();
            try {
              state.activeFicha = await timedApi(() =>
                API.post(`/fichas/${encodeURIComponent(f.numero_ticket)}/incidencia/`, {
                  descripcion_incidencia: box.querySelector('#ca07-desc').value.trim(),
                })
              );
              closeModal();
              await loadFichasList();
              showToast('Incidencia reportada. Ficha en espera.', 'warning');
              await navigate('incidencias');
            } catch (err) {
              showToast(err.message, 'danger');
            }
          });
        }
      );
    });

    mainEl.querySelector('#btn-report-21459').addEventListener('click', () => {
      openModal(
        `
        <div class="card-header">
          <h2 class="card-title">${ico('shield')} Activar protocolo Ley N° 21.459</h2>
          <button type="button" class="btn btn-ghost btn-sm" data-close-modal aria-label="Cerrar">${ico('x')}</button>
        </div>
        <p style="font-size:13px;">Se suspenderá inmediatamente toda intervención sobre el dispositivo sin alterar metadatos y quedará bloqueado bajo cadena de custodia del Docente encargado.</p>
        <div style="display:flex; gap:8px; justify-content:flex-end;">
          <button type="button" class="btn btn-outline" data-close-modal>Cancelar</button>
          <button type="button" class="btn btn-danger" id="btn-confirm-21459">Activar retención legal</button>
        </div>
        `,
        box => {
          box.querySelector('#btn-confirm-21459').addEventListener('click', async () => {
            try {
              state.activeFicha = await timedApi(() =>
                API.post(`/fichas/${encodeURIComponent(f.numero_ticket)}/hallazgo-ilicito/`, {})
              );
              closeModal();
              await loadFichasList();
              showToast('Protocolo Ley N° 21.459 activado.', 'danger');
              await navigate('taller');
            } catch (err) {
              showToast(err.message, 'danger');
            }
          });
        }
      );
    });
  }

  // ---------------------------------------------------------------------------
  // VISTA 5: BITÁCORA HISTÓRICA INMUTABLE & TRANSICIONES
  // ---------------------------------------------------------------------------
  function renderBitacoraScreen() {
    const f = state.activeFicha;
    if (!f) return;
    const canAddNote = ['TECNICO', 'DOCENTE_PO'].includes(state.auth.rol);

    mainEl.innerHTML = `
      ${ticketStripHtml(f)}
      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">${ico('fileText')} Bitácora técnica e historial de estados</h2>
            <p class="card-subtitle">Registro histórico de solo lectura posterior para trazabilidad completa de la orden</p>
          </div>
        </div>

        <div>
          <div style="font-size:12px; font-weight:500; margin-bottom:6px; color:var(--ink-secondary);">Flujo de estados</div>
          <div class="state-flow">
            ${ALL_STATES.map(st => {
              let cls = 'state-chip';
              if (st === f.estado) cls += ' current';
              else if ((f.allowed_transitions || []).includes(st)) cls += ' allowed';
              return `<span class="${cls}">${esc(st)}</span>`;
            }).join('')}
          </div>
        </div>

        ${
          canAddNote
            ? `<form id="nota-form" style="display:flex; gap:8px; flex-wrap:wrap;">
                <input id="nota-txt" type="text" required placeholder="Registrar nueva observación técnica..." style="flex:1; min-width:240px;">
                <button type="submit" class="btn btn-primary">${ico('plus')} Agregar nota</button>
              </form>`
            : '<div class="notice notice-info"><span>La bitácora técnica se encuentra en modo lectura para Recepción.</span></div>'
        }

        <div class="form-grid">
          <div>
            <h3 style="font-size:13.5px; font-weight:600; margin-bottom:10px;">Observaciones (${(f.notas || []).length})</h3>
            <div class="timeline">
              ${(f.notas || [])
                .map(
                  n => `
                <div class="timeline-item">
                  <div class="timeline-meta"><strong>${esc(n.autor_nombre)}</strong> · <span>${esc(n.fecha)}</span></div>
                  <div style="font-size:13px;">${esc(n.contenido)}</div>
                </div>`
                )
                .join('')}
            </div>
          </div>
          <div>
            <h3 style="font-size:13.5px; font-weight:600; margin-bottom:10px;">Cambios de estado (${(f.transiciones || []).length})</h3>
            <div class="timeline">
              ${(f.transiciones || [])
                .map(
                  tr => `
                <div class="timeline-item">
                  <div class="timeline-meta"><strong>${esc(tr.actor_nombre)}</strong> · <span>${esc(tr.fecha)}</span></div>
                  <div style="font-size:13px;"><span class="mono">${esc(tr.estado_origen)}</span> &rarr; <span class="mono">${esc(tr.estado_destino)}</span></div>
                </div>`
                )
                .join('')}
            </div>
          </div>
        </div>
      </div>
    `;

    const form = mainEl.querySelector('#nota-form');
    if (form) {
      form.addEventListener('submit', async ev => {
        ev.preventDefault();
        try {
          state.activeFicha = await timedApi(() =>
            API.post(`/fichas/${encodeURIComponent(f.numero_ticket)}/notas/`, {
              contenido: mainEl.querySelector('#nota-txt').value.trim(),
            })
          );
          showToast('Nota registrada en bitácora.', 'success');
          renderBitacoraScreen();
        } catch (err) {
          showToast(err.message, 'danger');
        }
      });
    }
  }

  // ---------------------------------------------------------------------------
  // VISTA 6: CONTROL DE CALIDAD Y VERIFICACIÓN FINAL
  // ---------------------------------------------------------------------------
  function renderPruebaScreen() {
    const f = state.activeFicha;
    if (!f) return;
    const gate = f.quality_gate || { ok: false, reason: 'Estado pendiente de verificación' };
    const alreadyReady = ['Listo para entrega', 'Entregado conforme', 'En custodia'].includes(f.estado);

    mainEl.innerHTML = `
      ${ticketStripHtml(f)}
      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">${ico('checkCircle')} Control de calidad final</h2>
            <p class="card-subtitle">Comparación de funcionamiento respecto a la prueba inicial registrada en recepción</p>
          </div>
        </div>

        ${
          !gate.ok && !alreadyReady
            ? `<div class="notice notice-danger">
                <span>${esc(gate.reason)}</span>
                <button type="button" class="btn btn-outline btn-sm" id="btn-back-taller">Ir al checklist</button>
              </div>`
            : `<div class="notice notice-success">
                <span>Checklist completado (${f.checklist_total}/${f.checklist_total} tareas). Equipo habilitado para certificación final.</span>
              </div>`
        }

        <form id="verif-form" class="form-grid">
          <label>Condición final del equipo
            <select id="vf-cond" ${!gate.ok && !alreadyReady ? 'disabled' : ''}>
              ${['Enciende y opera perfectamente', 'Reparado con observaciones menores', 'Estable bajo prueba de estrés térmico']
                .map(c => `<option value="${esc(c)}" ${f.condicion_final === c ? 'selected' : ''}>${esc(c)}</option>`)
                .join('')}
            </select>
          </label>
          <label>Métricas post-servicio (Temperatura / SMART / Red)
            <input id="vf-metricas" type="text" required value="${esc(f.metricas_post_estres || 'CPU 52°C máx · SSD Salud 98% · Red OK')}" ${!gate.ok && !alreadyReady ? 'disabled' : ''}>
          </label>
          <label class="form-full">Comparación respecto al ingreso ("${esc(f.prueba_inicial)}")
            <textarea id="vf-comp" rows="2" required ${!gate.ok && !alreadyReady ? 'disabled' : ''}>${esc(f.comparacion_final || '')}</textarea>
          </label>
          <div id="vf-err" class="form-full"></div>
          <div class="form-full" style="display:flex; justify-content:flex-end;">
            <button type="submit" class="btn btn-success" ${!gate.ok && !alreadyReady ? 'disabled' : ''}>
              Aprobar y marcar listo para entrega
            </button>
          </div>
        </form>
      </div>
    `;

    const backBtn = mainEl.querySelector('#btn-back-taller');
    if (backBtn) backBtn.addEventListener('click', () => navigate('taller'));

    mainEl.querySelector('#verif-form').addEventListener('submit', async ev => {
      ev.preventDefault();
      const errEl = mainEl.querySelector('#vf-err');
      errEl.innerHTML = '';
      try {
        state.activeFicha = await timedApi(() =>
          API.post(`/fichas/${encodeURIComponent(f.numero_ticket)}/verificar-final/`, {
            condicion_final: mainEl.querySelector('#vf-cond').value,
            metricas_post_estres: mainEl.querySelector('#vf-metricas').value.trim(),
            comparacion_final: mainEl.querySelector('#vf-comp').value.trim(),
          })
        );
        await loadFichasList();
        showToast(`${f.numero_ticket} marcado como listo para entrega.`, 'success');
        renderPruebaScreen();
        renderHeaderAndBar();
      } catch (err) {
        errEl.innerHTML = `<div class="notice notice-danger"><span>${esc(err.message)}</span></div>`;
      }
    });
  }

  // ---------------------------------------------------------------------------
  // VISTA 7: AVISO DE RETIRO AL TITULAR
  // ---------------------------------------------------------------------------
  function renderAvisoScreen() {
    const f = state.activeFicha;
    if (!f) return;
    const prop = f.propietario || {};

    mainEl.innerHTML = `
      ${ticketStripHtml(f)}
      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">${ico('phone')} Aviso de retiro al titular</h2>
            <p class="card-subtitle">Teléfono: <strong>${esc(prop.telefono)}</strong> · Correo: <strong>${esc(prop.correo)}</strong></p>
          </div>
          <span class="badge-status ${f.correo_enviado ? 'badge-listo' : 'badge-recibido'}">
            ${f.correo_enviado ? 'Correo enviado' : 'Correo pendiente'}
          </span>
        </div>

        <div style="display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
          <button type="button" class="btn btn-outline" id="btn-wa-log">Registrar aviso WhatsApp</button>
          <span style="font-size:12.5px; color:var(--ink-secondary);">Último estado telefónico: <strong>${esc(f.estado_llamada || 'Pendiente')}</strong></span>
        </div>

        <form id="aviso-form" class="form-grid">
          <label>Resultado de llamada
            <select id="av-estado">
              ${['Contacto confirmado', 'Sin respuesta (1er intento)', 'Sin respuesta (2do intento - Derivar a Custodia)', 'Buzón de voz']
                .map(s => `<option value="${esc(s)}" ${f.estado_llamada === s ? 'selected' : ''}>${esc(s)}</option>`)
                .join('')}
            </select>
          </label>
          <label>Observación del contacto
            <input id="av-obs" type="text" placeholder="Ej: Titular confirma retiro antes de las 17:30 hrs.">
          </label>
          <div class="form-full" style="display:flex; justify-content:flex-end; gap:8px;">
            <button type="submit" class="btn btn-primary">Guardar registro de llamada</button>
            <button type="button" class="btn btn-outline" id="btn-go-step8">Ir a entrega</button>
          </div>
        </form>
      </div>
    `;

    mainEl.querySelector('#btn-go-step8').addEventListener('click', () => navigate('salida'));
    mainEl.querySelector('#btn-wa-log').addEventListener('click', async () => {
      try {
        state.activeFicha = await timedApi(() =>
          API.post(`/fichas/${encodeURIComponent(f.numero_ticket)}/aviso/`, { tipo: 'whatsapp' })
        );
        showToast('Notificación WhatsApp registrada.', 'success');
        renderAvisoScreen();
      } catch (err) {
        showToast(err.message, 'danger');
      }
    });
    mainEl.querySelector('#aviso-form').addEventListener('submit', async ev => {
      ev.preventDefault();
      try {
        state.activeFicha = await timedApi(() =>
          API.post(`/fichas/${encodeURIComponent(f.numero_ticket)}/aviso/`, {
            tipo: 'llamada',
            estado_llamada: mainEl.querySelector('#av-estado').value,
            observacion: mainEl.querySelector('#av-obs').value.trim(),
          })
        );
        showToast('Contacto telefónico guardado.', 'success');
        renderAvisoScreen();
      } catch (err) {
        showToast(err.message, 'danger');
      }
    });
  }

  // ---------------------------------------------------------------------------
  // VISTA 8: ENTREGA EN MESÓN & ENCUESTA DE SATISFACCIÓN
  // ---------------------------------------------------------------------------
  function renderSalidaScreen() {
    const f = state.activeFicha;
    if (!f) return;
    const isTercero = f.tipo_receptor === 'Tercero';

    mainEl.innerHTML = `
      ${ticketStripHtml(f)}
      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">${ico('package')} Prueba en mesón y entrega de equipo</h2>
            <p class="card-subtitle">Si retira un tercero, verifica su RUT y confirma la autorización telefónica con el titular</p>
          </div>
        </div>

        <form id="entrega-form" class="form-grid">
          <label>Persona que retira
            <select id="ent-tipo">
              <option value="Titular" ${!isTercero ? 'selected' : ''}>Titular original</option>
              <option value="Tercero" ${isTercero ? 'selected' : ''}>Tercero autorizado</option>
            </select>
          </label>
          <label>Resultado de entrega
            <select id="ent-res">
              <option value="Entregado conforme">Entregado conforme</option>
              <option value="Devuelto sin reparación">Devuelto sin reparación</option>
            </select>
          </label>

          <div id="tercero-box" class="form-full form-grid" style="${isTercero ? '' : 'display:none;'} background:var(--bg-sidebar); padding:14px; border:1px solid var(--border); border-radius:var(--radius-sm);">
            <label>Nombre completo del tercero
              <input id="ent-t-nom" type="text" value="${esc(f.tercero_nombre || '')}" placeholder="Ej: Francisca Soto">
            </label>
            <label>RUT del tercero
              <input id="ent-t-rut" type="text" value="${esc(f.tercero_rut || '')}" placeholder="15.890.123-4">
              <div class="rut-feedback" id="ent-t-rut-fb"></div>
            </label>
            <label class="checkbox-tile form-full">
              <input id="ent-t-auth" type="checkbox" ${f.tercero_autorizado_telefono ? 'checked' : ''}>
              <span>Confirmo llamada telefónica al titular (${esc(f.propietario?.telefono)}) autorizando el retiro.</span>
            </label>
          </div>

          <div id="ent-err" class="form-full"></div>
          <div class="form-full" style="display:flex; justify-content:flex-end; gap:8px;">
            <button type="button" class="btn btn-outline" id="btn-go-print">${ico('printer')} Comprobante</button>
            <button type="submit" class="btn btn-success">Confirmar entrega</button>
          </div>
        </form>
      </div>

      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">Encuesta de satisfacción</h2>
            <p class="card-subtitle">Evaluación del usuario al retirar su dispositivo</p>
          </div>
          ${f.encuesta ? `<span class="badge-status badge-listo">Evaluada: ${f.encuesta.estrellas}/5</span>` : ''}
        </div>
        <form id="survey-form" class="form-grid">
          <div class="form-full">
            <div style="font-size:12px; font-weight:500; margin-bottom:4px;">Calificación general</div>
            <div class="star-rating" id="survey-stars">
              ${[1, 2, 3, 4, 5].map(n => `<span class="star ${n <= state.surveyStars ? 'active' : ''}" data-star="${n}">★</span>`).join('')}
            </div>
          </div>
          <label>Claridad de la explicación técnica
            <select id="sv-claridad">
              <option value="Muy clara">Muy clara</option>
              <option value="Clara">Clara</option>
              <option value="Regular">Regular</option>
            </select>
          </label>
          <label>¿Recomendaría la Clínica del PC?
            <select id="sv-rec">
              <option value="Sí, totalmente">Sí, totalmente</option>
              <option value="Probablemente sí">Probablemente sí</option>
              <option value="No">No</option>
            </select>
          </label>
          <div class="form-full" style="display:flex; justify-content:flex-end;">
            <button type="submit" class="btn btn-primary btn-sm">Enviar encuesta</button>
          </div>
        </form>
      </div>
    `;

    const tipoSel = mainEl.querySelector('#ent-tipo');
    const tercBox = mainEl.querySelector('#tercero-box');
    tipoSel.addEventListener('change', () => {
      tercBox.style.display = tipoSel.value === 'Tercero' ? 'grid' : 'none';
    });
    bindLiveRutFeedback(mainEl.querySelector('#ent-t-rut'), mainEl.querySelector('#ent-t-rut-fb'));
    mainEl.querySelector('#btn-go-print').addEventListener('click', () => navigate('print'));

    mainEl.querySelectorAll('#survey-stars .star').forEach(st => {
      st.addEventListener('click', () => {
        state.surveyStars = Number(st.getAttribute('data-star'));
        mainEl.querySelectorAll('#survey-stars .star').forEach(s => {
          s.classList.toggle('active', Number(s.getAttribute('data-star')) <= state.surveyStars);
        });
      });
    });

    mainEl.querySelector('#entrega-form').addEventListener('submit', async ev => {
      ev.preventDefault();
      const errEl = mainEl.querySelector('#ent-err');
      errEl.innerHTML = '';
      try {
        state.activeFicha = await timedApi(() =>
          API.post(`/fichas/${encodeURIComponent(f.numero_ticket)}/entrega/`, {
            tipo_receptor: tipoSel.value,
            resultado: mainEl.querySelector('#ent-res').value,
            tercero_nombre: mainEl.querySelector('#ent-t-nom').value.trim(),
            tercero_rut: mainEl.querySelector('#ent-t-rut').value.trim(),
            tercero_autorizado_telefono: mainEl.querySelector('#ent-t-auth').checked,
          })
        );
        await loadFichasList();
        showToast(`Entrega registrada: ${state.activeFicha.resultado_entrega}.`, 'success');
        renderSalidaScreen();
        renderHeaderAndBar();
      } catch (err) {
        errEl.innerHTML = `<div class="notice notice-danger"><span>${esc(err.message)}</span></div>`;
      }
    });

    mainEl.querySelector('#survey-form').addEventListener('submit', async ev => {
      ev.preventDefault();
      try {
        await timedApi(() =>
          API.post(`/fichas/${encodeURIComponent(f.numero_ticket)}/encuesta/`, {
            estrellas: state.surveyStars,
            claridad: mainEl.querySelector('#sv-claridad').value,
            recomendaria: mainEl.querySelector('#sv-rec').value,
          })
        );
        await loadActiveFicha(f.numero_ticket);
        showToast('Encuesta registrada.', 'success');
        renderSalidaScreen();
      } catch (err) {
        showToast(err.message, 'danger');
      }
    });
  }

  // ---------------------------------------------------------------------------
  // VISTA 9: CUSTODIA NOCTURNA & ANONIMIZACIÓN 60 DÍAS
  // ---------------------------------------------------------------------------
  function renderCustodiaScreen() {
    const f = state.activeFicha;
    if (!f) return;
    const enCustodia = state.fichasList.filter(x => x.estado === 'En custodia');

    mainEl.innerHTML = `
      ${ticketStripHtml(f)}
      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">${ico('lock')} Custodia nocturna (18:00 hrs) y retención</h2>
            <p class="card-subtitle">Resguardo de equipos no retirados al cierre de jornada · Plazo legal máximo 60 días</p>
          </div>
          ${
            state.auth.rol === 'DOCENTE_PO'
              ? '<button type="button" class="btn btn-outline btn-sm" id="btn-anon-vencidos">Anonimizar vencidos (> 60 días)</button>'
              : ''
          }
        </div>

        <form id="custodia-form" class="form-grid">
          <label>Ubicación de resguardo
            <input id="cus-ubic" type="text" required value="${esc(f.ubicacion_custodia || 'Sala de Profesores · Segundo Piso (INACAP)')}">
          </label>
          <label>Responsable de custodia
            <input id="cus-resp" type="text" required value="${esc(f.responsable_custodia || 'Prof. Pablo E. Pesce Sánchez')}">
          </label>
          <div id="cus-err" class="form-full"></div>
          <div class="form-full" style="display:flex; justify-content:flex-end;">
            <button type="submit" class="btn btn-warning">Trasladar ${esc(f.numero_ticket)} a custodia</button>
          </div>
        </form>

        <div>
          <h3 style="font-size:13.5px; font-weight:600; margin-bottom:8px;">Equipos actualmente en custodia (${enCustodia.length})</h3>
          <table class="checklist-table">
            <thead>
              <tr><th>Ticket</th><th>Acta</th><th>Dispositivo</th><th>Titular</th><th>Ubicación</th></tr>
            </thead>
            <tbody>
              ${
                !enCustodia.length
                  ? '<tr><td colspan="5" style="color:var(--ink-muted);">No hay equipos en custodia actualmente.</td></tr>'
                  : enCustodia
                      .map(
                        c => `
                    <tr>
                      <td><span class="mono">${esc(c.numero_ticket)}</span></td>
                      <td><span class="mono">${esc(c.acta_custodia_numero || '—')}</span></td>
                      <td>${esc(c.dispositivo?.marca_modelo || '')}</td>
                      <td>${esc(c.propietario?.nombre_completo || '')}</td>
                      <td>${esc(c.ubicacion_custodia || '')}</td>
                    </tr>`
                      )
                      .join('')
              }
            </tbody>
          </table>
        </div>
      </div>
    `;

    const anonBtn = mainEl.querySelector('#btn-anon-vencidos');
    if (anonBtn) {
      anonBtn.addEventListener('click', async () => {
        try {
          const res = await timedApi(() => API.post('/custodia/anonimizar-vencidos/', {}));
          showToast(`Proceso ejecutado: ${res.anonimizados} registro(s) anonimizados.`, 'success');
          await loadFichasList();
          await loadActiveFicha(state.activeTicketNumber);
          renderCustodiaScreen();
        } catch (err) {
          showToast(err.message, 'danger');
        }
      });
    }

    mainEl.querySelector('#custodia-form').addEventListener('submit', async ev => {
      ev.preventDefault();
      const errEl = mainEl.querySelector('#cus-err');
      errEl.innerHTML = '';
      try {
        state.activeFicha = await timedApi(() =>
          API.post(`/fichas/${encodeURIComponent(f.numero_ticket)}/custodia/`, {
            ubicacion_custodia: mainEl.querySelector('#cus-ubic').value.trim(),
            responsable_custodia: mainEl.querySelector('#cus-resp').value.trim(),
          })
        );
        await loadFichasList();
        showToast(`Acta ${state.activeFicha.acta_custodia_numero} emitida.`, 'success');
        renderCustodiaScreen();
        renderHeaderAndBar();
      } catch (err) {
        errEl.innerHTML = `<div class="notice notice-danger"><span>${esc(err.message)}</span></div>`;
      }
    });
  }

  // ---------------------------------------------------------------------------
  // VISTA INCIDENCIAS Y RETENCIONES LEGALES
  // ---------------------------------------------------------------------------
  function renderIncidenciasScreen() {
    const f = state.activeFicha;
    if (!f) return;
    const activeInc = state.fichasList.filter(x => x.incidencia_activa || x.hallazgo_ilicito_ley_21459);
    const isDoc = state.auth.rol === 'DOCENTE_PO';

    mainEl.innerHTML = `
      ${ticketStripHtml(f)}
      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">${ico('alert')} Incidencias y retenciones legales</h2>
            <p class="card-subtitle">La reanudación o cierre anticipado de fichas retenidas es facultad exclusiva del Docente encargado</p>
          </div>
        </div>

        ${
          f.incidencia_activa || f.hallazgo_ilicito_ley_21459
            ? `
          <div class="owner-panel">
            <div class="notice ${f.hallazgo_ilicito_ley_21459 ? 'notice-danger' : 'notice-warning'}">
              <span><strong>${esc(f.numero_ticket)}:</strong> ${esc(f.descripcion_incidencia)}</span>
            </div>
            ${f.directriz_docente ? `<div><strong>Directriz emitida:</strong> ${esc(f.directriz_docente)}</div>` : ''}
            ${
              isDoc
                ? `
              <div style="display:flex; flex-direction:column; gap:10px;">
                <div style="display:flex; gap:8px; flex-wrap:wrap;">
                  <input id="inc-dir-txt" type="text" placeholder="Escribir directriz para el técnico..." style="flex:1; min-width:220px;">
                  <button type="button" class="btn btn-primary btn-sm" id="btn-emit-dir">Emitir directriz</button>
                </div>
                <div style="display:flex; gap:8px; flex-wrap:wrap;">
                  <button type="button" class="btn btn-success btn-sm" id="btn-inc-auth">Autorizar reanudación</button>
                  <button type="button" class="btn btn-danger btn-sm" id="btn-inc-devolver">Cerrar sin reparación</button>
                </div>
              </div>`
                : '<div class="notice notice-info"><span>Pendiente de resolución por parte del Docente encargado.</span></div>'
            }
          </div>`
            : '<div class="notice notice-success"><span>La ficha seleccionada no registra incidencias activas.</span></div>'
        }

        <div>
          <h3 style="font-size:13.5px; font-weight:600; margin-bottom:8px;">Casos abiertos en la jornada (${activeInc.length})</h3>
          <table class="checklist-table">
            <thead><tr><th>Ticket</th><th>Estado</th><th>Clasificación</th><th>Equipo</th><th></th></tr></thead>
            <tbody>
              ${
                !activeInc.length
                  ? '<tr><td colspan="5" style="color:var(--ink-muted);">Sin incidencias abiertas.</td></tr>'
                  : activeInc
                      .map(
                        a => `
                    <tr>
                      <td><span class="mono">${esc(a.numero_ticket)}</span></td>
                      <td><span class="badge-status ${statusBadgeClass(a.estado)}">${esc(a.estado)}</span></td>
                      <td>${a.hallazgo_ilicito_ley_21459 ? 'Retención Ley 21.459' : 'Falla imprevista'}</td>
                      <td>${esc(a.dispositivo?.marca_modelo || '')}</td>
                      <td><button type="button" class="btn btn-outline btn-sm" data-focus-inc="${esc(a.numero_ticket)}">Seleccionar</button></td>
                    </tr>`
                      )
                      .join('')
              }
            </tbody>
          </table>
        </div>
      </div>
    `;

    mainEl.querySelectorAll('[data-focus-inc]').forEach(b => {
      b.addEventListener('click', async () => {
        state.activeTicketNumber = b.getAttribute('data-focus-inc');
        await loadActiveFicha(state.activeTicketNumber);
        renderIncidenciasScreen();
        renderHeaderAndBar();
      });
    });

    const resolve = async body => {
      try {
        state.activeFicha = await timedApi(() =>
          API.post(`/fichas/${encodeURIComponent(f.numero_ticket)}/resolver-incidencia/`, body)
        );
        await loadFichasList();
        showToast('Resolución registrada.', 'success');
        renderIncidenciasScreen();
        renderHeaderAndBar();
      } catch (err) {
        showToast(err.message, 'danger');
      }
    };

    const bDir = mainEl.querySelector('#btn-emit-dir');
    if (bDir) bDir.addEventListener('click', () => resolve({ accion: 'directriz', directriz_docente: mainEl.querySelector('#inc-dir-txt').value.trim() }));
    const bAuth = mainEl.querySelector('#btn-inc-auth');
    if (bAuth) bAuth.addEventListener('click', () => resolve({ accion: 'autorizar' }));
    const bDev = mainEl.querySelector('#btn-inc-devolver');
    if (bDev) bDev.addEventListener('click', () => resolve({ accion: 'devolver' }));
  }

  // ---------------------------------------------------------------------------
  // COMPROBANTE IMPRIMIBLE
  // ---------------------------------------------------------------------------
  function renderPrintScreen() {
    const f = state.activeFicha;
    if (!f) return;
    mainEl.innerHTML = `
      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">${ico('printer')} Comprobante de atención — Clínica del PC INACAP</h2>
            <p class="card-subtitle">Orden <span class="mono">${esc(f.numero_ticket)}</span> · Dispositivo <span class="mono">${esc(f.dispositivo?.codigo_dispositivo)}</span> · Sede San Pedro de la Paz</p>
          </div>
          <button type="button" class="btn btn-primary btn-sm" id="btn-do-print">${ico('printer')} Imprimir / Guardar PDF</button>
        </div>
        <div class="form-grid">
          <div><strong>Titular:</strong> ${esc(f.propietario?.nombre_completo)} (<span class="mono">${esc(f.propietario?.rut)}</span>)</div>
          <div><strong>Estado:</strong> ${esc(f.estado)}</div>
          <div><strong>Equipo:</strong> ${esc(f.dispositivo?.marca_modelo)} (${esc(f.dispositivo?.tipo)})</div>
          <div><strong>N° de serie / Clon:</strong> <span class="mono">${esc(f.dispositivo?.numero_serie || f.dispositivo?.codigo_interno_clon || 'N/A')}</span></div>
          <div class="form-full"><strong>Problema declarado:</strong> ${esc(f.problema_declarado)}</div>
          <div class="form-full"><strong>Daños preexistentes:</strong> ${esc(f.danos_preexistentes)}</div>
          <div class="form-full"><strong>Accesorios:</strong> ${esc(f.accesorios)}</div>
          <div class="form-full"><strong>Servicios:</strong> ${esc((f.servicios || []).join(', '))}</div>
          <div class="form-full"><strong>Sello digital de consentimiento:</strong> <span class="mono">${esc(f.firma_hash_sha256 || 'Pendiente')}</span></div>
          ${f.acta_custodia_numero ? `<div class="form-full"><strong>Custodia:</strong> ${esc(f.acta_custodia_numero)} · ${esc(f.ubicacion_custodia)}</div>` : ''}
        </div>
      </div>
    `;
    mainEl.querySelector('#btn-do-print').addEventListener('click', () => window.print());
  }

  // ---------------------------------------------------------------------------
  // ADMINISTRACIÓN DOCENTE: PLANTILLAS & NÓMINA CSV
  // ---------------------------------------------------------------------------
  async function fetchAdminData() {
    try {
      const [pl, nom] = await Promise.all([
        timedApi(() => API.get('/admin/plantillas/')),
        timedApi(() => API.get('/admin/nomina/')),
      ]);
      state.adminPlantillas = pl;
      state.adminNomina = nom;
    } catch (err) {
      showToast(err.message, 'danger');
    }
  }

  function renderAdminScreen() {
    const plantillas = state.adminPlantillas || [];
    const nomina = state.adminNomina || { total: 0, activos: 0, estudiantes: [] };

    mainEl.innerHTML = `
      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">${ico('settings')} Plantillas de procedimientos técnicos</h2>
            <p class="card-subtitle">Versionado automático de tareas por servicio para nuevas fichas</p>
          </div>
        </div>
        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap:12px;">
          ${plantillas
            .map(
              p => `
            <div class="owner-panel">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <strong>${esc(p.nombre)}</strong>
                <span class="badge-status badge-preinscrito">v${p.version_actual}.0</span>
              </div>
              <textarea class="tpl-tasks" data-srv="${esc(p.nombre)}" rows="6">${esc((p.tareas || []).join('\n'))}</textarea>
              <button type="button" class="btn btn-primary btn-sm" data-save-tpl="${esc(p.nombre)}">Guardar nueva versión</button>
            </div>`
            )
            .join('')}
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">${ico('users')} Nómina de alumnos técnicos (CSV)</h2>
            <p class="card-subtitle">Habilitados en jornada: <strong>${nomina.activos}/${nomina.total}</strong></p>
          </div>
          <div style="display:flex; gap:8px; flex-wrap:wrap;">
            <button type="button" class="btn btn-outline btn-sm" id="btn-sim-65">Simular carga 65 alumnos</button>
            <button type="button" class="btn btn-danger btn-sm" id="btn-revoke-all">Revocar credenciales al cierre</button>
          </div>
        </div>

        <form id="csv-form" class="form-grid">
          <label class="form-full">Pegar filas CSV (RUT, Nombre, Sección)
            <textarea id="csv-text" rows="3" placeholder="20.456.789-1,Estudiante Prueba,TI3043-01"></textarea>
          </label>
          <label>Cargar archivo .csv
            <input id="csv-file" type="file" accept=".csv,text/csv">
          </label>
          <div style="display:flex; align-items:end; gap:8px; flex-wrap:wrap;">
            <button type="submit" class="btn btn-primary btn-sm">Importar nómina</button>
            <button type="button" class="btn btn-outline btn-sm" id="btn-inject-csv-test">Probar sanitización CSV</button>
          </div>
        </form>

        <div style="max-height:300px; overflow-y:auto;">
          <table class="checklist-table">
            <thead><tr><th>Usuario</th><th>Nombre</th><th>RUT</th><th>Sección</th><th>Token</th><th>Estado</th></tr></thead>
            <tbody>
              ${nomina.estudiantes
                .map(
                  e => `
                <tr>
                  <td><span class="mono">${esc(e.username)}</span></td>
                  <td>${esc(e.nombre)}</td>
                  <td><span class="mono">${esc(e.rut || '—')}</span></td>
                  <td>${esc(e.seccion)}</td>
                  <td><span class="mono">${esc(e.token_temporal_hash)}</span></td>
                  <td><span class="badge-status ${e.habilitado_jornada ? 'badge-listo' : 'badge-devuelto'}">${e.habilitado_jornada ? 'Habilitado' : 'Revocado'}</span></td>
                </tr>`
                )
                .join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;

    mainEl.querySelectorAll('[data-save-tpl]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const srv = btn.getAttribute('data-save-tpl');
        const ta = mainEl.querySelector(`.tpl-tasks[data-srv="${CSS.escape(srv)}"]`);
        const tareas = ta.value.split('\n').map(x => x.trim()).filter(Boolean);
        try {
          state.adminPlantillas = await timedApi(() => API.put('/admin/plantillas/', { servicio: srv, tareas }));
          showToast(`Plantilla "${srv}" actualizada.`, 'success');
          renderAdminScreen();
        } catch (err) {
          showToast(err.message, 'danger');
        }
      });
    });

    mainEl.querySelector('#btn-sim-65').addEventListener('click', async () => {
      try {
        state.adminNomina = await timedApi(() => API.post('/admin/nomina/importar-csv/', { simular_65: true }));
        showToast('Nómina de 65 alumnos cargada.', 'success');
        renderAdminScreen();
      } catch (err) {
        showToast(err.message, 'danger');
      }
    });

    mainEl.querySelector('#btn-revoke-all').addEventListener('click', async () => {
      try {
        state.adminNomina = await timedApi(() => API.post('/admin/nomina/revocar-masivo/', {}));
        showToast('Accesos temporales revocados.', 'warning');
        renderAdminScreen();
      } catch (err) {
        showToast(err.message, 'danger');
      }
    });

    mainEl.querySelector('#btn-inject-csv-test').addEventListener('click', () => {
      mainEl.querySelector('#csv-text').value = '20.456.789-1,=cmd|\'/C calc\'!A0,TI3043-01\n19.111.222-9,+SUM(1+1),TI3043-02';
    });

    mainEl.querySelector('#csv-form').addEventListener('submit', async ev => {
      ev.preventDefault();
      const fileIn = mainEl.querySelector('#csv-file');
      try {
        if (fileIn.files && fileIn.files[0]) {
          const fd = new FormData();
          fd.append('file', fileIn.files[0]);
          state.adminNomina = await timedApi(() => API.postForm('/admin/nomina/importar-csv/', fd));
        } else {
          state.adminNomina = await timedApi(() =>
            API.post('/admin/nomina/importar-csv/', { csv_text: mainEl.querySelector('#csv-text').value })
          );
        }
        showToast('Nómina importada correctamente.', 'success');
        renderAdminScreen();
      } catch (err) {
        showToast(err.message, 'danger');
      }
    });
  }

  // ---------------------------------------------------------------------------
  // MÉTRICAS & EXPORTACIÓN CSV
  // ---------------------------------------------------------------------------
  async function fetchMetricas() {
    try {
      state.metricasData = await timedApi(() => API.get('/metricas/'));
    } catch (err) {
      showToast(err.message, 'danger');
    }
  }

  function renderMetricasScreen() {
    const m = state.metricasData || {
      total: 0, recepcionados: 0, en_taller: 0, entregados: 0, en_custodia: 0, incidencias_activas: 0, servicios: {},
    };
    const srvs = m.servicios || {};
    const maxS = Math.max(1, ...Object.values(srvs));

    mainEl.innerHTML = `
      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">${ico('chart')} Resumen operativo de la jornada</h2>
            <p class="card-subtitle">Indicadores agregados directamente sobre PostgreSQL</p>
          </div>
          <button type="button" class="btn btn-outline btn-sm" id="btn-export-csv">${ico('download')} Exportar respaldo CSV</button>
        </div>

        <div class="kpi-row">
          <div class="kpi-card"><div class="kpi-num">${m.total}</div><div class="kpi-label">Total fichas</div></div>
          <div class="kpi-card"><div class="kpi-num">${m.recepcionados}</div><div class="kpi-label">Recepcionados</div></div>
          <div class="kpi-card"><div class="kpi-num">${m.en_taller}</div><div class="kpi-label">En taller</div></div>
          <div class="kpi-card"><div class="kpi-num">${m.entregados}</div><div class="kpi-label">Entregados</div></div>
          <div class="kpi-card"><div class="kpi-num">${m.en_custodia}</div><div class="kpi-label">En custodia</div></div>
          <div class="kpi-card"><div class="kpi-num">${m.incidencias_activas}</div><div class="kpi-label">Incidencias</div></div>
        </div>

        <div>
          <h3 style="font-size:13.5px; font-weight:600; margin-bottom:10px;">Demanda por tipo de servicio</h3>
          ${Object.entries(srvs)
            .map(([name, cnt]) => {
              const pct = Math.round((cnt / maxS) * 100);
              return `
                <div style="margin-bottom:10px;">
                  <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
                    <span>${esc(name)}</span><span class="mono">${cnt}</span>
                  </div>
                  <div style="background:var(--bg-subtle); border-radius:999px; height:8px; overflow:hidden;">
                    <div style="background:var(--brand); width:${pct}%; height:100%;"></div>
                  </div>
                </div>`;
            })
            .join('')}
        </div>
      </div>
    `;

    mainEl.querySelector('#btn-export-csv').addEventListener('click', async () => {
      try {
        await timedApi(() => API.downloadFile('/metricas/exportar-csv/', 'respaldo_clinica_pc.csv'));
        showToast('Respaldo CSV descargado.', 'success');
      } catch (err) {
        showToast(err.message, 'danger');
      }
    });
  }

  // ---------------------------------------------------------------------------
  // AUDITORÍA OWASP TOP 10:2025 & PATRONES GoF (PANEL DOCENTE)
  // ---------------------------------------------------------------------------
  async function fetchAuditoria() {
    try {
      state.auditoriaData = await timedApi(() => API.get('/seguridad/auditoria/'));
    } catch (err) {
      showToast(err.message, 'danger');
    }
  }

  function renderSeguridadScreen() {
    const a = state.auditoriaData || { database_engine: 'PostgreSQL', gof_patterns: [], logs: [] };
    mainEl.innerHTML = `
      <div class="card">
        <div class="card-header">
          <div>
            <h2 class="card-title">${ico('shield')} Auditoría de seguridad, cumplimiento y arquitectura</h2>
            <p class="card-subtitle">Base activa: <span class="mono">${esc(a.database_engine)}</span> · Última latencia medida: <span class="mono">${esc(state.lastLatency)} s</span> (RNF07 ≤ 2.0 s)</p>
          </div>
          <button type="button" class="btn btn-outline btn-sm" id="btn-refresh-sec">${ico('refresh')} Actualizar</button>
        </div>

        <div class="kpi-row">
          ${(a.gof_patterns || [])
            .map(
              g => `
            <div class="kpi-card">
              <div class="kpi-label">${esc(g.pattern)}</div>
              <div style="font-weight:650; color:var(--brand); font-size:13.5px;">${esc(g.class)}</div>
              <div style="font-size:12px; color:var(--ink-secondary);">${esc(g.purpose)}</div>
            </div>`
            )
            .join('')}
        </div>

        <div style="max-height:380px; overflow-y:auto;">
          <table class="checklist-table">
            <thead><tr><th>Fecha</th><th>Nivel</th><th>Evento</th><th>Actor</th><th>Ruta</th><th>Detalle</th></tr></thead>
            <tbody>
              ${(a.logs || [])
                .map(
                  l => `
                <tr>
                  <td class="table-date">${esc(l.fecha)}</td>
                  <td><span class="badge-status ${l.nivel === 'CRITICAL' ? 'badge-espera' : l.nivel === 'WARN' ? 'badge-recibido' : 'badge-listo'}">${esc(l.nivel)}</span></td>
                  <td><span class="mono">${esc(l.evento)}</span></td>
                  <td>${esc(l.actor_nombre || '—')}</td>
                  <td><span class="mono">${esc(l.ruta || '—')}</span></td>
                  <td>${esc(l.detalle)}</td>
                </tr>`
                )
                .join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;

    mainEl.querySelector('#btn-refresh-sec').addEventListener('click', async () => {
      await fetchAuditoria();
      renderSeguridadScreen();
    });
  }

  // ---------------------------------------------------------------------------
  // EVENTOS DE SHELL & BOOTSTRAP
  // ---------------------------------------------------------------------------
  sideNavEl.addEventListener('click', ev => {
    const btn = ev.target.closest('[data-nav]');
    if (btn) navigate(btn.getAttribute('data-nav'));
  });

  mainEl.addEventListener('click', ev => {
    const stBtn = ev.target.closest('[data-step-goto]');
    if (stBtn && !stBtn.disabled) {
      navigate(stBtn.getAttribute('data-step-goto'));
    }
  });

  ticketSelectEl.addEventListener('change', async () => {
    state.activeTicketNumber = ticketSelectEl.value;
    await loadActiveFicha(state.activeTicketNumber);
    renderAll();
  });

  btnOpenAuth.addEventListener('click', openAuthModal);
  btnScenarios.addEventListener('click', openScenariosModal);

  btnLogout.addEventListener('click', async () => {
    try {
      await timedApi(() => API.post('/auth/logout/', {}));
      showToast('Sesión cerrada.', 'info');
      await refreshSession(false);
    } catch (err) {
      showToast(err.message, 'danger');
    }
  });

  modalBackdropEl.addEventListener('click', ev => {
    if (ev.target === modalBackdropEl) closeModal();
  });

  document.addEventListener('keydown', ev => {
    if (ev.key === 'Escape' && modalBackdropEl.classList.contains('open')) {
      closeModal();
    }
  });

  document.addEventListener('DOMContentLoaded', async () => {
    renderAll();
    await checkHealth();
    await refreshSession(false);
  });
})();
