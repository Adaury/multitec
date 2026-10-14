import { forwardRef, useEffect, useState, type AudioHTMLAttributes, type ImgHTMLAttributes } from 'react'
import { api } from '../lib/api'

/** `/uploads` exige sesión: un <img src> no puede mandar el token, así que el archivo se descarga con
 * la sesión y se muestra desde una URL local. Se guarda por ruta para no bajar la misma foto dos veces. */
const blobUrls = new Map<string, Promise<string>>()

function uploadPath(filePath: string): string {
  return `/${filePath.replace(/^.*uploads\//, 'uploads/')}`
}

function loadUpload(filePath: string): Promise<string> {
  const path = uploadPath(filePath)
  let cached = blobUrls.get(path)
  if (!cached) {
    cached = api
      .get<Blob>(path, { baseURL: '/', responseType: 'blob' })
      .then((res) => URL.createObjectURL(res.data))
      .catch((err) => {
        blobUrls.delete(path) // que un fallo (red, sesión vencida) no quede guardado
        throw err
      })
    blobUrls.set(path, cached)
  }
  return cached
}

function useUploadUrl(filePath: string): string | undefined {
  const [url, setUrl] = useState<string>()
  useEffect(() => {
    let cancelled = false
    setUrl(undefined)
    loadUpload(filePath)
      .then((value) => !cancelled && setUrl(value))
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [filePath])
  return url
}

type ImageProps = Omit<ImgHTMLAttributes<HTMLImageElement>, 'src'> & { filePath: string }

export const UploadImage = forwardRef<HTMLImageElement, ImageProps>(function UploadImage(
  { filePath, alt, ...props },
  ref,
) {
  const url = useUploadUrl(filePath)
  // Mientras llega la foto se reserva el espacio con el mismo tamaño, sin icono de imagen rota.
  return <img ref={ref} src={url} alt={alt} {...props} style={{ ...props.style, visibility: url ? undefined : 'hidden' }} />
})

type AudioProps = Omit<AudioHTMLAttributes<HTMLAudioElement>, 'src'> & { filePath: string }

export function UploadAudio({ filePath, ...props }: AudioProps) {
  const url = useUploadUrl(filePath)
  return <audio src={url} {...props} />
}
