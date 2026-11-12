'use strict';

window.ClinicaAPI = (() => {
  // Si el frontend corre desacoplado en Live Server (:5500), apunta al backend Django (:8000);
  // si es servido por el mismo origen, usa ruta relativa.
  const API_BASE =
    window.location.port === '5500'
      ? 'http://127.0.0.1:8000/api/v1'
      : '/api/v1';

  class ApiError extends Error {
    constructor(status, message, data = null) {
      super(message);
      this.status = status;
      this.data = data;
    }
  }

  function getCookie(name) {
    const m = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
    return m ? decodeURIComponent(m[1]) : '';
  }

  async function ensureCsrf() {
    if (!getCookie('csrftoken')) {
      await fetch(`${API_BASE}/auth/csrf/`, { credentials: 'include' });
    }
    return getCookie('csrftoken');
  }

  async function request(path, { method = 'GET', body = null, isFormData = false } = {}) {
    const headers = {};
    if (method !== 'GET' && method !== 'HEAD') {
      headers['X-CSRFToken'] = await ensureCsrf();
    }
    let finalBody = body;
    if (body && !isFormData && typeof body !== 'string') {
      headers['Content-Type'] = 'application/json';
      finalBody = JSON.stringify(body);
    }

    const res = await fetch(`${API_BASE}${path}`, {
      method,
      credentials: 'include',
      headers,
      body: finalBody,
    });

    const contentType = res.headers.get('content-type') || '';
    const payload = contentType.includes('application/json') ? await res.json() : await res.text();

    if (!res.ok) {
      let msg = `Error HTTP ${res.status}`;
      if (payload && typeof payload === 'object') {
        if (payload.detail) msg = payload.detail;
        else {
          const firstKey = Object.keys(payload)[0];
          const val = payload[firstKey];
          msg = Array.isArray(val) ? val[0] : String(val);
        }
      }
      throw new ApiError(res.status, msg, payload);
    }
    return payload;
  }

  async function downloadFile(path, filename) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: 'GET',
      credentials: 'include',
    });
    if (!res.ok) {
      let msg = `Error HTTP ${res.status}`;
      try {
        const err = await res.json();
        if (err && err.detail) msg = err.detail;
      } catch (_) {}
      throw new ApiError(res.status, msg);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  return {
    API_BASE,
    ApiError,
    get: (p) => request(p),
    post: (p, b) => request(p, { method: 'POST', body: b }),
    postForm: (p, fd) => request(p, { method: 'POST', body: fd, isFormData: true }),
    put: (p, b) => request(p, { method: 'PUT', body: b }),
    downloadFile,
    downloadCsvUrl: `${API_BASE}/metricas/exportar-csv/`,
  };
})();
