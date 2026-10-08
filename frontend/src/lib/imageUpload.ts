const MAX_SIDE = 1600 // píxeles del lado mayor: sobra para ver detalle en pantalla y en el PDF
const JPEG_QUALITY = 0.82
const SKIP_BELOW_BYTES = 300 * 1024 // una foto ya liviana no vale la pena recomprimirla

/** Reduce una foto antes de subirla. Las fotos del celular pesan 4-12 MB; en datos móviles eso
 * tarda y se cuelga la pantalla. Redimensionada a 1600 px y en JPEG baja a ~200-400 KB sin
 * perder lo que importa en un levantamiento. Respeta la orientación EXIF. Si el navegador no puede
 * decodificarla (p. ej. HEIC fuera de Safari) o el resultado no es más chico, devuelve la original. */
export async function shrinkImage(file: File): Promise<File> {
  if (!file.type.startsWith('image/') || file.type === 'image/gif' || file.size < SKIP_BELOW_BYTES) return file
  try {
    const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' })
    const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height))
    const width = Math.max(1, Math.round(bitmap.width * scale))
    const height = Math.max(1, Math.round(bitmap.height * scale))

    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    const ctx = canvas.getContext('2d')
    if (!ctx) return file
    ctx.fillStyle = '#fff' // un PNG con transparencia no debe quedar negro al pasar a JPEG
    ctx.fillRect(0, 0, width, height)
    ctx.drawImage(bitmap, 0, 0, width, height)
    bitmap.close()

    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/jpeg', JPEG_QUALITY))
    if (!blob || blob.size >= file.size) return file
    const name = file.name.replace(/\.[^.]+$/, '') || 'foto'
    return new File([blob], `${name}.jpg`, { type: 'image/jpeg', lastModified: Date.now() })
  } catch {
    return file
  }
}
