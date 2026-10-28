# Videos de la Ayuda

Los videos de **Ayuda** (`/ayuda` y la pantalla de entrada) viven ya hechos en `frontend/public/videos/` (un MP4 y una
portada JPG por tema). Estos scripts sirven para **regrabarlos cuando cambie la pantalla**: la app se recorre sola, con
datos de ejemplo y en un entorno aislado (nunca toca tu base ni tus clientes), con cursor visible, subtítulos y voz.

## Qué hace cada archivo

| Archivo | Para qué |
| --- | --- |
| `scenes.json` | El guion: una escena por línea, con el texto que se narra y se subtitula. |
| `tts.ps1` | Genera la voz de cada escena (Windows, voz «Microsoft Helena», español) en `wav/`. |
| `make_photo.py` | Dibuja la foto de ejemplo (fachada de un colmado) que se sube en el video. |
| `record.mjs` | Recorre la app con Playwright y graba `out/admin.webm` (escritorio) y `out/tech.webm` (iPhone). |
| `build.mjs` | Acelera las esperas de la IA, sincroniza la voz con cada escena y arma `out/guia.mp4`. |
| `cut.mjs` | Corta la guía en videos cortos por tema y los deja en `public/videos/` con su portada. |

## Cómo regrabar

Necesitas: Windows (la voz), `ffmpeg` en el PATH, Ollama corriendo con `llama3.2` (la IA se usa de verdad en el video) y
el `venv` del backend.

1. Si cambiaste el guion: `powershell -File scripts/videos/tts.ps1` (genera las voces) y
   `backend\venv\Scripts\python.exe scripts\videos\make_photo.py` (la foto, una sola vez).
2. Levanta el entorno aislado de grabación (base nueva y datos de ejemplo, en otros puertos que los de siempre):

   ```bash
   E2E_TMP_DIR=scripts/videos/env E2E_API_PORT=8400 E2E_ADMIN_PASSWORD=Guia-Video-2026x node e2e/scripts/start-backend.mjs
   E2E_API_TARGET=http://127.0.0.1:8400 npx vite --port 5480 --strictPort
   ```

3. `node scripts/videos/record.mjs` — tarda unos 6 minutos. Imprime cada escena y avisa si alguna falló
   (`! escena …`). `DEBUG_NET=1` muestra las peticiones; `STOP_AFTER=ia` se detiene tras la escena de la IA.
4. `node scripts/videos/build.mjs out/guia.mp4` y `node scripts/videos/cut.mjs`.
5. Si cambiaste textos o duraciones, actualiza `src/lib/tutoriales.ts` (transcripciones y duración que se muestran).
6. Apaga el entorno de grabación (los puertos 8400 y 5480).

Las carpetas `out/`, `wav/` y `env/` y la foto `fachada.png` son temporales y no se suben al repositorio.

## Cosas que aprendimos grabando

- El cursor se vuelve a medir justo antes de cada clic y cada elemento se centra en pantalla: con la barra superior fija,
  «lo justo» dejaba el botón tapado y el clic caía en la barra.
- Se escribe con `pressSequentially` sobre el campo, no con el teclado suelto: el foco puede haberse movido.
- Los videos son MP4 (H.264 + AAC) y no WebM: es lo que reproduce el iPhone. El servidor responde a `Range`, necesario
  para que Safari pueda avanzar y retroceder.
