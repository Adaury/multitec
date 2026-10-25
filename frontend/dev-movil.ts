import type { Plugin } from 'vite'

// Vista de programación: sirve en /dev/movil una página con la app dentro de un marco de iPhone,
// para ver en tiempo real (con HMR) cómo queda en el celular mientras se edita el código.
// Solo existe con `vite` (apply: 'serve'); no entra en la versión compilada ni en el túnel de producción.
const PAGE = /* html */ `<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Multitec · Vista móvil</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin: 0; height: 100vh; display: flex; flex-direction: column; background: #0b0d12; color: #e6e8ee;
         font: 14px/1.4 system-ui, sans-serif; }
  header { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 10px 14px; background: #141821;
           border-bottom: 1px solid #232938; }
  header h1 { font-size: 14px; margin: 0 10px 0 0; font-weight: 600; }
  select, input, button { background: #1c2230; color: inherit; border: 1px solid #2c3447; border-radius: 8px;
                          padding: 6px 10px; font: inherit; }
  button { cursor: pointer; }
  button:hover { background: #252d40; }
  input { flex: 1; min-width: 140px; max-width: 320px; }
  main { flex: 1; min-height: 0; display: flex; align-items: center; justify-content: center; overflow: hidden; }
  #stage { position: relative; transform-origin: center center; flex: none; }
  #frame { position: relative; background: #000; border: 12px solid #1a1c22; border-radius: 62px;
           box-shadow: 0 0 0 2px #3a3f4d, 0 30px 80px rgba(0,0,0,.6); overflow: hidden; }
  #frame iframe { display: block; width: 100%; height: 100%; border: 0; background: #fff; }
  #island { position: absolute; top: 10px; left: 50%; width: 120px; height: 34px; margin-left: -60px;
            background: #000; border-radius: 20px; pointer-events: none; z-index: 2; }
  #frame.land #island { display: none; }
  #info { color: #8b93a7; margin-left: auto; font-variant-numeric: tabular-nums; }
</style>
</head>
<body>
<header>
  <h1>Vista móvil</h1>
  <select id="device"></select>
  <button id="rotate" title="Girar">⟳ Girar</button>
  <input id="url" value="/" spellcheck="false" />
  <button id="go">Ir</button>
  <button id="reload">Recargar</button>
  <span id="info"></span>
</header>
<main>
  <div id="stage"><div id="frame"><div id="island"></div><iframe id="app" title="App"></iframe></div></div>
</main>
<script>
  const DEVICES = {
    'iPhone 17 Pro Max': [440, 956],
    'iPhone 17 Pro': [402, 874],
    'iPhone 16e': [390, 844],
    'iPhone SE': [375, 667],
  };
  const $ = (id) => document.getElementById(id);
  const store = { get: (k, d) => { try { return localStorage.getItem(k) ?? d } catch { return d } },
                  set: (k, v) => { try { localStorage.setItem(k, v) } catch {} } };
  const device = $('device'), frame = $('frame'), app = $('app'), stage = $('stage'), url = $('url');
  for (const name of Object.keys(DEVICES)) device.add(new Option(name, name));
  device.value = DEVICES[store.get('mv-device')] ? store.get('mv-device') : 'iPhone 17 Pro Max';
  let land = store.get('mv-land') === '1';
  url.value = store.get('mv-url', '/');

  function layout() {
    const [w, h] = DEVICES[device.value];
    const [cw, ch] = land ? [h, w] : [w, h];
    frame.style.width = cw + 24 + 'px';
    frame.style.height = ch + 24 + 'px';
    frame.classList.toggle('land', land);
    const box = document.querySelector('main').getBoundingClientRect();
    const s = Math.min(1, (box.width - 40) / (cw + 24), (box.height - 40) / (ch + 24));
    stage.style.transform = 'scale(' + s + ')';
    $('info').textContent = cw + '×' + ch + ' · ' + Math.round(s * 100) + '%';
  }
  function go(path) {
    store.set('mv-url', path);
    app.src = path;
  }
  // Mantiene el campo sincronizado con la ruta real al navegar dentro de la app.
  app.addEventListener('load', () => {
    try { const p = app.contentWindow.location.pathname + app.contentWindow.location.search;
          url.value = p; store.set('mv-url', p); } catch {}
  });
  device.onchange = () => { store.set('mv-device', device.value); layout(); };
  $('rotate').onclick = () => { land = !land; store.set('mv-land', land ? '1' : '0'); layout(); };
  $('go').onclick = () => go(url.value || '/');
  url.onkeydown = (e) => { if (e.key === 'Enter') go(url.value || '/'); };
  $('reload').onclick = () => app.contentWindow.location.reload();
  addEventListener('resize', layout);
  layout();
  go(url.value);
</script>
</body>
</html>`

export function devMovil(): Plugin {
  return {
    name: 'multitec-dev-movil',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.url?.split('?')[0] !== '/dev/movil') return next()
        res.setHeader('Content-Type', 'text/html; charset=utf-8')
        res.end(PAGE)
      })
    },
  }
}
