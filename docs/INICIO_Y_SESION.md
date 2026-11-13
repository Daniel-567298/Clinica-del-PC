# Corrección de inicio y sesión

13 de noviembre de 2026.

La sede San Pedro de la Paz, el evento inicial y sus cinco fichas ya existían. No se crearon sustitutos ni se volvió a ejecutar la carga demo sobre la base local.

Se reprodujo la pantalla vacía al combinar la interfaz actual con una versión anterior de `api.js`: la carga se detenía con `API.setEvento is not a function`. Las solicitudes a sedes y eventos respondían correctamente, pero el error impedía actualizar la pantalla. También se verificó en el registro del servidor que un cierre de sesión exitoso había sido seguido de intentos sin sesión, mientras el botón seguía visible.

La página ahora referencia sus archivos JavaScript y CSS con una versión calculada a partir de su contenido. Se evita reutilizar archivos antiguos al actualizar la aplicación. La carga inicial muestra su progreso; si falla el catálogo se muestra **Reintentar carga**, manteniendo visible el estado correcto de la sesión.

Al salir se limpia inmediatamente el estado interno y se oculta el botón; mientras la solicitud está en curso se impiden clics repetidos. Una solicitud de salida sin sesión devuelve el estado público sin registrar una salida ficticia ni un error de credenciales. Las salidas con sesión mantienen la validación CSRF.

Para utilizarlo: abrir http://127.0.0.1:8000/ y recargar una vez con **Ctrl + F5**. Debe aparecer **San Pedro de la Paz → Jornada inicial de demostración**. Iniciar sesión normalmente; no es necesario usar **Casos de prueba** ni crear otra sede.

Se verificaron en Edge los tres perfiles: entrada pública, inicio de sesión desde el formulario, persistencia al recargar, acceso a Días y participantes y cierre de sesión. Se comprobó además la recuperación de un fallo de catálogo durante la salida y que la nueva página no solicita el archivo API bajo su URL antigua.

Los cambios son locales y no requieren una migración de base de datos.
