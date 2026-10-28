// Monta el video final: acelera las esperas, pone la narración en cada escena y une escritorio + iPhone.
import fs from 'node:fs'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const OUT = path.join(here, 'out')
const timelines = JSON.parse(fs.readFileSync(path.join(OUT, 'timeline.json'), 'utf8'))
const FINAL = process.argv[2] ?? path.join(OUT, 'guia.mp4')

function wavSeconds(id) {
  const buf = fs.readFileSync(path.join(here, 'wav', `${id}.wav`))
  return buf.readUInt32LE(buf.indexOf('data') + 4) / buf.readUInt32LE(28)
}
function ffmpeg(args) {
  const r = spawnSync('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', ...args], { stdio: 'inherit' })
  if (r.status !== 0) throw new Error('ffmpeg falló: ' + args.slice(0, 6).join(' '))
}
function duration(file) {
  const r = spawnSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', file], { encoding: 'utf8' })
  return parseFloat(r.stdout)
}

/** Parte de un video: acelera cada tramo `fast` lo justo para que la narración de su escena quepa y no se encime. */
function buildPart(name, vw, vh) {
  const tl = timelines[name]
  const src = path.join(OUT, `${name}.webm`)
  const total = duration(src)
  const scenes = tl.scenes.map((s, i) => ({ ...s, end: tl.scenes[i + 1]?.start ?? total }))
  // Tramos con su factor de velocidad
  const windows = tl.fast.map((f) => {
    const scene = scenes.find((s) => f.start >= s.start && f.start < s.end)
    const fastLen = f.end - f.start
    const nonFast = scene.end - scene.start - fastLen
    const target = Math.max(wavSeconds(scene.id) + 1, nonFast + 3)
    const newLen = Math.max(2, target - nonFast)
    return { ...f, speed: Math.max(1, fastLen / newLen), newLen: fastLen / Math.max(1, fastLen / newLen) }
  })
  const mapT = (t) => {
    let shift = 0
    for (const w of windows) {
      if (t >= w.end) shift += w.end - w.start - w.newLen
      else if (t > w.start) shift += (t - w.start) * (1 - 1 / w.speed)
    }
    return t - shift
  }
  // Segmentos del video: normales y acelerados
  const segs = []
  let cursor = 0
  for (const w of windows) {
    if (w.start > cursor) segs.push({ a: cursor, b: w.start, speed: 1 })
    segs.push({ a: w.start, b: w.end, speed: w.speed })
    cursor = w.end
  }
  segs.push({ a: cursor, b: total, speed: 1 })
  const fc = []
  segs.forEach((s, i) => {
    fc.push(`[0:v]trim=start=${s.a.toFixed(3)}:end=${s.b.toFixed(3)},setpts=(PTS-STARTPTS)/${s.speed.toFixed(4)},fps=25[s${i}]`)
  })
  fc.push(`${segs.map((_, i) => `[s${i}]`).join('')}concat=n=${segs.length}:v=1:a=0,scale=-2:720:flags=lanczos,pad=1280:720:(ow-iw)/2:0:color=0x0b1220,format=yuv420p[v]`)
  // Audio: cada narración empieza donde empieza su escena (tiempo ya acelerado)
  const inputs = ['-i', src]
  const starts = []
  scenes.forEach((s, i) => {
    inputs.push('-i', path.join(here, 'wav', `${s.id}.wav`))
    const ms = Math.round((mapT(s.start) + 0.35) * 1000)
    fc.push(`[${i + 1}:a]aresample=44100,pan=stereo|c0=c0|c1=c0,adelay=${ms}|${ms}[a${i}]`)
    starts.push(`[a${i}]`)
  })
  fc.push(`${starts.join('')}amix=inputs=${scenes.length}:normalize=0:duration=longest[a]`)
  const outFile = path.join(OUT, `part_${name}.mp4`)
  const newTotal = mapT(total)
  ffmpeg([
    ...inputs,
    '-filter_complex', fc.join(';'),
    '-map', '[v]', '-map', '[a]',
    '-t', newTotal.toFixed(2),
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '21', '-c:a', 'aac', '-b:a', '160k', '-r', '25',
    outFile,
  ])
  console.log(`${name}: ${total.toFixed(0)} s grabados → ${newTotal.toFixed(0)} s (acelerado ${windows.length} tramos)`)
  // Dónde cae cada escena en el video final de esta parte (para cortar los videos por tema)
  finalScenes.push(
    ...scenes.map((s) => ({ id: s.id, part: name, start: mapT(s.start), end: mapT(s.end) })),
  )
  return outFile
}

const finalScenes = []
const parts = [buildPart('admin', 1280, 720), buildPart('tech', 390, 844)]
// La parte del técnico va después de la del administrador: sus tiempos se desplazan lo que dura la primera.
const adminLength = duration(parts[0])
for (const s of finalScenes) if (s.part === 'tech') ((s.start += adminLength), (s.end += adminLength))
fs.writeFileSync(path.join(OUT, 'scenes_final.json'), JSON.stringify(finalScenes, null, 2))
const list = path.join(OUT, 'concat.txt')
fs.writeFileSync(list, parts.map((p) => `file '${p.replace(/\\/g, '/')}'`).join('\n'))
ffmpeg(['-f', 'concat', '-safe', '0', '-i', list, '-c:v', 'libx264', '-preset', 'medium', '-crf', '21', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', FINAL])
console.log('Video final:', FINAL, `(${duration(FINAL).toFixed(0)} s, ${(fs.statSync(FINAL).size / 1048576).toFixed(1)} MB)`)
