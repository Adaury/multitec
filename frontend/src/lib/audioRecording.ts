/** Formato de grabación que soporta este navegador. iPhone solo graba mp4/aac; Chrome y Android, webm/opus. */
export function pickMimeType(): string {
  if (typeof MediaRecorder === 'undefined') return ''
  for (const type of ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4']) {
    if (MediaRecorder.isTypeSupported(type)) return type
  }
  return ''
}

/** Extensión del archivo según lo realmente grabado: el servidor transcribe por el tipo, y un mp4 de
 * iPhone subido como ".webm" confunde al decodificador. */
export function audioExtension(mimeType: string): string {
  return mimeType.includes('mp4') ? 'm4a' : 'webm'
}
