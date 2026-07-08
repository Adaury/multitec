import type { ButtonHTMLAttributes, InputHTMLAttributes, LabelHTMLAttributes, ReactNode, TextareaHTMLAttributes } from 'react'

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-3xl bg-white p-5 shadow-sm ring-1 ring-black/5 dark:bg-gray-900 dark:ring-white/10 ${className}`}>
      {children}
    </div>
  )
}

export function Button({
  variant = 'primary',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost' }) {
  const base = 'w-full rounded-2xl px-5 py-4 text-base font-medium transition active:scale-[0.98] disabled:opacity-50'
  const styles = {
    primary: 'bg-brand-blue text-white hover:bg-brand-blue-dark',
    secondary: 'bg-brand-gray text-gray-800 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-100 dark:hover:bg-gray-700',
    ghost: 'bg-transparent text-brand-blue hover:bg-brand-gray dark:hover:bg-gray-800',
  }
  return <button className={`${base} ${styles[variant]} ${className}`} {...props} />
}

export function Modal({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
}) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 md:items-center md:p-4">
      <div
        className="max-h-[90vh] w-full overflow-y-auto rounded-t-3xl bg-white p-5 shadow-xl ring-1 ring-black/5 md:max-w-lg md:rounded-3xl dark:bg-gray-900 dark:ring-white/10"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full px-2 py-1 text-gray-400 hover:bg-brand-gray hover:text-gray-600 dark:hover:bg-gray-800"
            aria-label="Cerrar"
          >
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block text-left">
      <span className="mb-1 block text-sm font-medium text-gray-600 dark:text-gray-400">{label}</span>
      {children}
    </label>
  )
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 outline-none focus:border-brand-blue focus:ring-2 focus:ring-brand-blue/20 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
    />
  )
}

export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 outline-none focus:border-brand-blue focus:ring-2 focus:ring-brand-blue/20 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
    />
  )
}

export function Label(props: LabelHTMLAttributes<HTMLLabelElement>) {
  return <label {...props} />
}

export function Badge({ children, tone = 'blue' }: { children: ReactNode; tone?: 'blue' | 'gray' | 'green' | 'red' | 'amber' }) {
  const tones = {
    blue: 'bg-blue-50 text-brand-blue dark:bg-blue-950 dark:text-blue-300',
    gray: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300',
    green: 'bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300',
    red: 'bg-red-50 text-red-600 dark:bg-red-950 dark:text-red-300',
    amber: 'bg-amber-50 text-amber-600 dark:bg-amber-950 dark:text-amber-300',
  }
  return <span className={`rounded-full px-3 py-1 text-xs font-medium ${tones[tone]}`}>{children}</span>
}

export function IconButton({
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={`flex h-9 w-9 items-center justify-center rounded-full bg-brand-gray text-gray-500 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700 ${className}`}
      {...props}
    />
  )
}
