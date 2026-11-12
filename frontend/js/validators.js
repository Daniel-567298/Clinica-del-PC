'use strict';

window.ClinicaValidators = (() => {
  const esc = (s = '') =>
    String(s).replace(/[&<>"']/g, c => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
    }[c]));

  const normalizeRut = (r = '') => String(r).replace(/[^0-9kK]/g, '').toUpperCase();

  function validarRutChileno(rutCompleto) {
    if (!rutCompleto) return false;
    const limpio = normalizeRut(rutCompleto);
    if (limpio.length < 8 || limpio.length > 9) return false;
    const cuerpo = limpio.slice(0, -1);
    const dv = limpio.slice(-1);
    if (!/^\d+$/.test(cuerpo)) return false;
    let suma = 0;
    let multiplo = 2;
    for (let i = cuerpo.length - 1; i >= 0; i--) {
      suma += multiplo * parseInt(cuerpo.charAt(i), 10);
      multiplo = multiplo < 7 ? multiplo + 1 : 2;
    }
    const dvEsp = 11 - (suma % 11);
    const dvCalc = dvEsp === 11 ? '0' : (dvEsp === 10 ? 'K' : String(dvEsp));
    return dv === dvCalc;
  }

  function bindLiveRutFeedback(inputEl, feedbackEl) {
    if (!inputEl || !feedbackEl) return;
    const update = () => {
      const val = inputEl.value.trim();
      if (!val) {
        feedbackEl.textContent = '';
        inputEl.classList.remove('valid-rut', 'invalid-rut');
        return;
      }
      if (validarRutChileno(val)) {
        feedbackEl.innerHTML = '<span class="rut-valid">RUT válido</span>';
        inputEl.classList.add('valid-rut');
        inputEl.classList.remove('invalid-rut');
      } else {
        feedbackEl.innerHTML = '<span class="rut-invalid">Dígito verificador incorrecto</span>';
        inputEl.classList.add('invalid-rut');
        inputEl.classList.remove('valid-rut');
      }
    };
    inputEl.addEventListener('input', update);
    if (inputEl.value.trim()) update();
  }

  return { esc, normalizeRut, validarRutChileno, bindLiveRutFeedback };
})();
