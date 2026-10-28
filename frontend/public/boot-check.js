/* Detector de fallos de arranque. Va aparte del resto de la app y en JavaScript sencillo (sin sintaxis nueva) A PROPÓSITO:
 * tiene que funcionar justo cuando lo demás NO arranca (una pantalla vacía sin ningún mensaje, que es lo peor que le puede
 * pasar a alguien en la obra). Hace dos cosas:
 *   1. Si la app no dibuja nada en 8 s, o dibuja y se vacía, muestra un aviso con el error y dos botones (Recargar y
 *      Actualizar la app), en vez de dejar la pantalla negra.
 *   2. Manda el error al servidor (/api/client-errors) para poder leerlo en el log: desde fuera no se ve lo que pasa en
 *      un teléfono. Solo manda el mensaje, el archivo y el navegador; nunca datos de la persona. */
(function () {
  var sent = {}
  var lastError = ''

  function clean(value, max) {
    return String(value == null ? '' : value).replace(/[\r\n\t]+/g, ' ').slice(0, max)
  }

  function send(kind, message, detail) {
    var key = kind + '|' + message
    if (sent[key]) return
    sent[key] = true
    var body = JSON.stringify({
      kind: clean(kind, 30),
      message: clean(message, 500),
      detail: clean(detail, 1500),
      url: clean(location.pathname + location.search, 300),
    })
    try {
      if (navigator.sendBeacon && navigator.sendBeacon('/api/client-errors', new Blob([body], { type: 'application/json' }))) return
    } catch (e) {
      /* se intenta de otra forma */
    }
    try {
      var xhr = new XMLHttpRequest()
      xhr.open('POST', '/api/client-errors')
      xhr.setRequestHeader('Content-Type', 'application/json')
      xhr.send(body)
    } catch (e2) {
      /* sin red: no hay nada más que hacer */
    }
  }

  window.addEventListener(
    'error',
    function (event) {
      var target = event.target
      if (target && target !== window && (target.src || target.href)) {
        // No es un error de código sino un archivo que no cargó (red, bloqueo, archivo que ya no existe)
        lastError = 'no cargó ' + (target.src || target.href)
        send('recurso', lastError, target.tagName || '')
        return
      }
      var where = (event.filename || '') + ':' + (event.lineno || 0) + ':' + (event.colno || 0)
      lastError = (event.message || 'error') + ' (' + where + ')'
      send('error', event.message || 'error', where + ' ' + ((event.error && event.error.stack) || ''))
    },
    true,
  )
  window.addEventListener('unhandledrejection', function (event) {
    var reason = event.reason
    var message = (reason && reason.message) || String(reason)
    lastError = message
    send('promesa', message, (reason && reason.stack) || '')
  })
  document.addEventListener('securitypolicyviolation', function (event) {
    send('csp', event.violatedDirective + ' bloqueó ' + event.blockedURI, event.sourceFile || '')
  })

  var overlay = null

  function button(text, primary, onClick) {
    var b = document.createElement('button')
    b.textContent = text
    b.style.cssText =
      'display:block;width:100%;margin:10px 0 0;padding:14px;border-radius:14px;border:0;font:600 16px system-ui,sans-serif;' +
      (primary ? 'background:#0a63e2;color:#fff;' : 'background:#e5e7eb;color:#111;')
    b.addEventListener('click', onClick)
    return b
  }

  function refreshApp() {
    var done = function () {
      location.reload()
    }
    try {
      var jobs = []
      if (navigator.serviceWorker && navigator.serviceWorker.getRegistrations) {
        jobs.push(
          navigator.serviceWorker.getRegistrations().then(function (list) {
            return Promise.all(
              list.map(function (r) {
                return r.unregister()
              }),
            )
          }),
        )
      }
      if (window.caches && caches.keys) {
        jobs.push(
          caches.keys().then(function (keys) {
            return Promise.all(
              keys.map(function (k) {
                return caches.delete(k)
              }),
            )
          }),
        )
      }
      Promise.all(jobs).then(done, done)
    } catch (e) {
      done()
    }
  }

  function showFallback(reason) {
    if (overlay) return
    overlay = document.createElement('div')
    overlay.setAttribute('role', 'alert')
    overlay.style.cssText =
      'position:fixed;left:0;top:0;right:0;bottom:0;z-index:2147483647;background:#fff;color:#111;padding:28px 22px;' +
      'font:16px/1.45 system-ui,sans-serif;overflow:auto;'
    var title = document.createElement('h1')
    title.textContent = 'No se pudo abrir la aplicación'
    title.style.cssText = 'font-size:22px;margin:0 0 10px'
    var text = document.createElement('p')
    text.textContent =
      'Tus datos y levantamientos sin enviar siguen guardados. Prueba recargar; si sigue igual, pulsa «Actualizar la app».'
    var detail = document.createElement('pre')
    detail.textContent = reason || 'La pantalla quedó vacía.'
    detail.style.cssText =
      'white-space:pre-wrap;word-break:break-word;background:#f3f4f6;border-radius:10px;padding:10px;font-size:12px;color:#444'
    overlay.appendChild(title)
    overlay.appendChild(text)
    overlay.appendChild(
      button('Recargar', true, function () {
        location.reload()
      }),
    )
    overlay.appendChild(button('Actualizar la app', false, refreshApp))
    overlay.appendChild(detail)
    document.body.appendChild(overlay)
  }

  function hideFallback() {
    if (overlay && overlay.parentNode) overlay.parentNode.removeChild(overlay)
    overlay = null
  }

  var hadContent = false
  var seconds = 0
  var timer = setInterval(function () {
    seconds++
    var root = document.getElementById('root')
    var hasContent = !!(root && root.children.length)
    if (hasContent) {
      hadContent = true
      hideFallback() // la app llegó tarde pero llegó: el aviso ya no hace falta
    } else if (!overlay && (hadContent || seconds >= 8)) {
      send(hadContent ? 'se-vacio' : 'no-arranco', lastError || 'la pantalla quedó vacía', 'segundos=' + seconds)
      showFallback(lastError)
    }
    if (seconds >= 40) clearInterval(timer)
  }, 1000)
})()
