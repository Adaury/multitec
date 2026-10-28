// Corta el video completo en videos cortos por tema, con su portada, dentro de frontend/public/videos.
import fs from 'node:fs'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const OUT = path.join(here, 'out')
const DEST = path.resolve(here, '../../public/videos')
fs.mkdirSync(DEST, { recursive: true })
const scenes = JSON.parse(fs.readFileSync(path.join(OUT, 'scenes_final.json'), 'utf8'))
const at = (id) => scenes.find((s) => s.id === id)

const TEMAS = [
  { id: '00-guia-completa', desde: 'intro', hasta: 'fin' },
  { id: '01-entrar-al-sistema', desde: 'login', hasta: 'inicio' },
  { id: '02-cliente-y-proyecto', desde: 'cliente', hasta: 'proyecto' },
  { id: '03-levantamiento-y-puntos', desde: 'levantamiento', hasta: 'marcar' },
  { id: '04-cotizacion-con-ia', desde: 'ia', hasta: 'cotizacion' },
  { id: '05-precios-y-comparar', desde: 'precios', hasta: 'comparar' },
  { id: '06-mapa-y-como-llegar', desde: 'mapa', hasta: 'mapa' },
  { id: '07-plataforma-y-demos', desde: 'plataforma', hasta: 'demo' },
  { id: '08-el-tecnico-en-el-iphone', desde: 'tecnico', hasta: 'tecnico2' },
]

function ffmpeg(args) {
  const r = spawnSync('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', ...args], { stdio: 'inherit' })
  if (r.status !== 0) throw new Error('ffmpeg falló')
}
function duration(file) {
  const r = spawnSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', file], { encoding: 'utf8' })
  return parseFloat(r.stdout)
}

const resumen = []
for (const t of TEMAS) {
  const start = at(t.desde).start
  const end = at(t.hasta).end
  const mp4 = path.join(DEST, `${t.id}.mp4`)
  ffmpeg([
    '-i', path.join(OUT, 'guia.mp4'), '-ss', start.toFixed(2), '-to', end.toFixed(2),
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '23', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', mp4,
  ])
  ffmpeg(['-i', mp4, '-ss', '2.5', '-frames:v', '1', '-vf', 'scale=960:-2', '-q:v', '4', path.join(DEST, `${t.id}.jpg`)])
  const s = duration(mp4)
  resumen.push({ id: t.id, segundos: Math.round(s), mb: +(fs.statSync(mp4).size / 1048576).toFixed(1) })
}
console.table(resumen)
console.log('Total MB:', resumen.reduce((a, r) => a + r.mb, 0).toFixed(1))
